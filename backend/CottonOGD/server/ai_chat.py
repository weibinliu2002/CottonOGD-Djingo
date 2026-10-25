"""
AI Chat 对话服务：用户问题 -> 大模型 -> Tool Calling -> CottonOGD 查询 -> 最终回答。

链路（第一版）：
    Django AI API -> 大模型 API(openai SDK) -> Tool Calling
    -> CottonOGD server/ai_tools.py -> MySQL / Meilisearch
    -> 工具结果回传大模型 -> 自然语言回答

安全约束：
  - 大模型从不直连 MySQL / Meilisearch，只能通过 TOOL_REGISTRY 中的函数查询；
  - API key / base_url 只来自 settings（.env），不进代码、不进日志、不下发前端；
  - 工具结果过大时截断，防止撑爆上下文。
"""
import json
import logging

from django.conf import settings
from django.core.cache import cache
from openai import OpenAI

from CottonOGD.server.ai_tools import TOOL_SPECS, execute_tool

logger = logging.getLogger(__name__)

# 单个工具结果回传给 LLM 的最大字符数（超出截断并标注）
MAX_TOOL_RESULT_CHARS = 20000
# 服务端会话历史最大轮数（一轮 = user + assistant 两条）
MAX_HISTORY_TURNS = 20
# 单条消息最大字符数（用户输入 + 每条历史）
MAX_MESSAGE_CHARS = 8000
# 服务端会话历史在 Redis 中的 key 前缀与有效期
HISTORY_KEY_PREFIX = 'ai_chat_history:'
HISTORY_TTL = 60 * 60 * 24  # 24 小时

SYSTEM_PROMPT = (
    '你是 CottonOGD（棉花组学数据库）的智能助手。CottonOGD 收录了 258 个棉花基因组，'
    '包含基因、转录因子（TF/TR 家族）、功能注释（UniProt/Pfam/eggNOG）、GO、KEGG 等数据。\n'
    '回答数据相关问题时必须调用工具查询真实数据，严禁编造基因 ID、坐标或注释。\n'
    '工具使用要点：\n'
    '- 精确/模糊基因 ID 查找 -> search_gene；拿单个基因详情（坐标、注释、GO/KEGG）-> get_gene_detail；\n'
    '- 转录因子家族问题（NAC、MYB、WRKY 等）-> search_transcription_factor，family 留空可拿到家族列表；\n'
    '- genome 参数是物种全名（如 G.hirsutumAD1_TM-1_HAU_v1.1），不确定时可留空或部分匹配；\n'
    '- 工具返回错误（如基因不存在、物种名歧义）时，根据错误信息调整参数重试，或向用户澄清。\n'
    '查询不到的数据要如实说明。用中文回答，简洁、面向科研用户；'
    '如引用 jbrowse_url，请保持工具返回的相对路径原样输出，不要自行补全域名。'
)


class AIChatNotConfigured(Exception):
    """LLM 未配置（缺 API key 或模型名）。"""


def get_client():
    """
    构造 OpenAI 兼容客户端（模块级缓存）。

    所有凭证来自 settings.AI_CHAT_*（.env），SDK 内部走 HTTPS 传输，
    本项目代码不出现任何明文 HTTP 调用与密钥。
    """
    if not settings.AI_CHAT_ENABLED:
        raise AIChatNotConfigured('AI Chat 未配置：请在 .env 中设置 AI_CHAT_API_KEY 与 AI_CHAT_MODEL')
    client = getattr(get_client, '_client', None)
    if client is None:
        client = OpenAI(
            api_key=settings.AI_CHAT_API_KEY,
            base_url=settings.AI_CHAT_BASE_URL,
            timeout=settings.AI_CHAT_TIMEOUT,
            max_retries=1,
        )
        get_client._client = client
    return client


def _clip(text, limit=MAX_MESSAGE_CHARS):
    return text if len(text) <= limit else text[:limit] + '…(内容过长已截断)'


# =============================================================================
# 服务端会话历史（Redis，挂在认证 uuid 下）
# 前端只带 token/cookie、传 message；历史由服务端加载与追加。
# =============================================================================

def _history_key(uuid):
    return f'{HISTORY_KEY_PREFIX}{uuid}'


def load_history(uuid):
    """取该会话的历史消息列表（已清洗），无历史返回空列表。"""
    if not uuid:
        return []
    return _sanitize_history(cache.get(_history_key(uuid), []))


def save_history(uuid, messages):
    """覆盖写入会话历史，超出上限的旧轮次自动丢弃。"""
    if not uuid:
        return
    cache.set(_history_key(uuid), messages[-MAX_HISTORY_TURNS * 2:], HISTORY_TTL)


def clear_history(uuid):
    """清空会话历史（开始新话题时调用）。"""
    if uuid:
        cache.delete(_history_key(uuid))


def _sanitize_history(history):
    """清洗前端传入的历史消息：只保留 role/content，限制长度与条数。"""
    if not isinstance(history, list):
        return []
    clean = []
    for item in history[-MAX_HISTORY_TURNS:]:
        if not isinstance(item, dict):
            continue
        role = item.get('role')
        content = item.get('content')
        if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
            clean.append({'role': role, 'content': _clip(content)})
    return clean


def _tool_result_message(tool_call_id, name, result):
    """把工具结果包成 role=tool 消息，超长截断。"""
    payload = json.dumps(result, ensure_ascii=False, default=str)
    if len(payload) > MAX_TOOL_RESULT_CHARS:
        payload = payload[:MAX_TOOL_RESULT_CHARS] + ' …(结果过长已截断)'
    return {'role': 'tool', 'tool_call_id': tool_call_id, 'content': payload}


def run_ai_chat(message, uuid=None, reset=False):
    """
    执行一次完整对话（含多轮工具调用），历史由服务端按 uuid 自动管理。

    Args:
        message: 用户本次提问
        uuid: 认证会话 ID（ClientTokenMiddleware 由 token/cookie 桥接而来），
              用于加载/保存服务端对话历史
        reset: True 时丢弃历史、从新对话开始

    Returns:
        {'answer': str, 'tool_calls': [...], 'history_turns': int}

    Raises:
        AIChatNotConfigured: 未配置 LLM。
        openai.OpenAIError: 上游模型调用失败（由视图转 502）。
    """
    client = get_client()

    if reset:
        clear_history(uuid)
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    messages.extend(load_history(uuid))
    messages.append({'role': 'user', 'content': _clip(str(message or '').strip())})

    tool_trace = []
    max_rounds = settings.AI_CHAT_MAX_TOOL_ROUNDS
    answer = ''

    for _round in range(max_rounds + 1):
        response = client.chat.completions.create(
            model=settings.AI_CHAT_MODEL,
            messages=messages,
            tools=TOOL_SPECS,
            tool_choice='auto',
        )
        choice = response.choices[0]
        assistant_msg = choice.message

        # 无工具调用 -> 得到最终回答
        if not assistant_msg.tool_calls:
            answer = assistant_msg.content or ''
            break

        # 记录 assistant 的工具调用请求，再逐个执行并回填 tool 消息
        messages.append({
            'role': 'assistant',
            'content': assistant_msg.content or '',
            'tool_calls': [{
                'id': tc.id,
                'type': 'function',
                'function': {
                    'name': tc.function.name,
                    'arguments': tc.function.arguments,
                },
            } for tc in assistant_msg.tool_calls],
        })

        for tc in assistant_msg.tool_calls:
            result, elapsed_ms = execute_tool(tc.function.name, tc.function.arguments)
            tool_trace.append({
                'name': tc.function.name,
                'arguments': tc.function.arguments,
                'elapsed_ms': elapsed_ms,
            })
            logger.info('AI chat tool %s %sms -> %s', tc.function.name, elapsed_ms,
                        'error' if 'error' in result else 'ok')
            messages.append(_tool_result_message(tc.id, tc.function.name, result))

    # 工具轮数用尽：要求模型基于已有信息直接作答
    if not answer:
        messages.append({
            'role': 'user',
            'content': '（系统提示：已达到本次对话工具调用轮数上限，请基于已获得的查询结果直接回答。）',
        })
        response = client.chat.completions.create(
            model=settings.AI_CHAT_MODEL,
            messages=messages,
        )
        answer = response.choices[0].message.content or ''

    # 成功完成才追加历史；失败（OpenAIError 等）不会走到这里
    stored = load_history(uuid)
    stored.append({'role': 'user', 'content': _clip(str(message or '').strip())})
    stored.append({'role': 'assistant', 'content': _clip(answer)})
    save_history(uuid, stored)

    return {
        'answer': answer,
        'tool_calls': tool_trace,
        'history_turns': len(stored) // 2,
    }
