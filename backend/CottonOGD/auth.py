"""
客户端认证：token + cookie 双通道，Redis 会话存储。

- POST /login/ 签发 token（secrets.token_urlsafe），同时：
  1) 返回给前端（Authorization: Bearer <token> 使用）；
  2) 种 HttpOnly + SameSite=Lax cookie（auth_token），同站请求自动携带。
- ClientTokenMiddleware 在请求进入视图前校验 token（header 优先、cookie 兜底），
  校验通过后把对应 uuid 注入 request.META['HTTP_UUID']——
  既有视图中的 `request.headers.get('uuid')` / UuidManager 校验零改动继续生效。
- 旧的裸 uuid header 校验在过渡期继续可用（同一 Redis 会话），后续可收紧。
"""
import logging
import secrets

from django.core.cache import cache

logger = logging.getLogger(__name__)

TOKEN_PREFIX = 'auth_token:'
TOKEN_TTL = 60 * 60 * 24 * 7  # 7 天
COOKIE_NAME = 'auth_token'


def issue_token(uuid: str) -> str:
    """为会话 uuid 签发 token，落 Redis。"""
    token = secrets.token_urlsafe(32)
    cache.set(f'{TOKEN_PREFIX}{token}', uuid, TOKEN_TTL)
    return token


def revoke_token(token: str) -> None:
    cache.delete(f'{TOKEN_PREFIX}{token}')


def resolve_token(token: str):
    """token -> uuid；无效返回 None。"""
    if not token:
        return None
    return cache.get(f'{TOKEN_PREFIX}{token}')


def extract_token(request):
    """Authorization: Bearer 优先，其次 auth_token cookie。"""
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return request.COOKIES.get(COOKIE_NAME)


class ClientTokenMiddleware:
    """
    token -> uuid 桥接中间件：
    校验通过且请求未带 uuid header 时注入 HTTP_UUID，
    使既有视图的 uuid 校验逻辑无需改动即可识别已认证客户端。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = extract_token(request)
        uuid = resolve_token(token)
        if uuid and not request.META.get('HTTP_UUID'):
            request.META['HTTP_UUID'] = uuid
        return self.get_response(request)
