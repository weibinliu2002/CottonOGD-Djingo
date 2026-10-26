"""
AI Chat 视图：POST /CottonOGD_api/ai/chat/

对话历史由服务端管理（Redis，挂在认证 uuid 下，24 小时有效）：
前端只需携带 token（Authorization: Bearer）或同站 cookie，每次只传 message。
传 "clear_history": true 可丢弃历史、开始新话题。

请求体：
    {
      "message": "帮我找一下 NAC 相关的转录因子",   # 必填
      "clear_history": false                        # 可选，true 时清空服务端历史
    }

响应：
    {
      "success": true,
      "answer": "……自然语言回答……",
      "tool_calls": [{"name": "search_transcription_factor", "arguments": "...", "elapsed_ms": 12}],
      "history_turns": 3        # 服务端当前保留的对话轮数
    }

认证与全站一致（Authorization: Bearer <token> 或 auth_token cookie，
由 ClientTokenMiddleware 桥接为 uuid header）。LLM 凭证只存在于服务端 .env。
"""
import json
import logging
import traceback

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from openai import OpenAIError

from CottonOGD.server.ai_chat import AIChatNotConfigured, run_ai_chat
from CottonOGD.views.base import UuidManager

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 256 * 1024  # 请求体上限
MAX_MESSAGE_CHARS = 8000


@require_http_methods(["POST"])
@csrf_exempt
def ai_chat(request):
    # 1) 认证（与 proxy_search 一致）
    uuid = request.headers.get('uuid')
    if uuid not in UuidManager.uuid_storage:
        return JsonResponse({'success': False, 'error': 'uuid is required'}, status=400)

    # 2) 未配置 LLM 时明确告知，而不是 500
    if not settings.AI_CHAT_ENABLED:
        return JsonResponse({
            'success': False,
            'error': 'AI Chat 未启用：请在服务端 .env 配置 AI_CHAT_API_KEY / AI_CHAT_MODEL',
        }, status=503)

    # 3) 请求体校验
    if len(request.body or b'') > MAX_BODY_BYTES:
        return JsonResponse({'success': False, 'error': 'request body too large'}, status=413)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'invalid JSON body'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'success': False, 'error': 'request body must be a JSON object'}, status=400)

    message = str(data.get('message') or '').strip()
    if not message:
        return JsonResponse({'success': False, 'error': 'message is required'}, status=400)
    if len(message) > MAX_MESSAGE_CHARS:
        return JsonResponse(
            {'success': False, 'error': f'message too long (max {MAX_MESSAGE_CHARS} chars)'},
            status=400)

    # 4) 执行对话（历史由服务端按 uuid 自动加载/追加）
    try:
        result = run_ai_chat(message, uuid=uuid, reset=bool(data.get('clear_history')))
    except AIChatNotConfigured as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=503)
    except OpenAIError as exc:
        logger.error('AI chat 上游调用失败: %s', exc, exc_info=True)
        # 不回传 exc 细节，避免泄露 base_url / 鉴权信息
        return JsonResponse({'success': False, 'error': '大模型服务调用失败，请稍后重试'},
                            status=502)
    except Exception as exc:  # noqa: BLE001
        logger.error('AI chat 内部错误: %s\n%s', exc, traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'内部错误：{exc}'}, status=500)

    return JsonResponse({
        'success': True,
        'answer': result['answer'],
        'tool_calls': result['tool_calls'],
        'history_turns': result['history_turns'],
    })
