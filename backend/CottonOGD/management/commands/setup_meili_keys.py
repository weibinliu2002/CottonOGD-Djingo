"""
幂等创建或查询 Meilisearch 的 search-only API key，用于前端直连。
Key 限制：name=frontend-search, actions=['search'], indexes=['genemaster'], expires_at=None。
"""
from __future__ import annotations
import sys
from django.core.management.base import BaseCommand, CommandError


def _obj_to_dict(obj):
    """把 pydantic Key 对象（meilisearch 0.40.x）或 dict 都统一成 dict。"""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    # pydantic v1/v2 都有 model_dump / dict
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    if hasattr(obj, 'dict'):
        return obj.dict()
    # 兜底：尝试属性访问转 dict
    data = {}
    for attr in ('uid', 'key', 'name', 'description', 'actions',
                 'indexes', 'expiresAt', 'expires_at', 'created_at',
                 'updated_at'):
        if hasattr(obj, attr):
            data[attr] = getattr(obj, attr)
    return data


class Command(BaseCommand):
    help = '幂等创建/查询 frontend-search (search-only) API key，并供前端使用。'

    def add_arguments(self, parser):
        parser.add_argument('--print-only', action='store_true',
                            help='只打印 settings 中已有的 frontend key，不调用 Meili。')
        parser.add_argument('--json', action='store_true',
                            help='以 JSON 格式输出 key 信息。')

    def handle(self, *args, **options):
        from django.conf import settings
        from CottonOGD.config.meilisearch_config import MeilisearchConfig

        frontend_key = (getattr(settings, 'MEILISEARCH_FRONTEND_API_KEY', '') or '').strip()

        if options['print_only']:
            payload = {
                'from_env': bool(frontend_key),
                'frontend_api_key': frontend_key or None,
            }
            self._print(payload, options['json'])
            return

        if frontend_key:
            self.stdout.write(self.style.WARNING(
                'skip: MEILISEARCH_FRONTEND_API_KEY 已配置，沿用环境变量值（未在 Meili 中创建新 key）。'
                ' 如需强制新建请先清空该环境变量。'))
            self._print({
                'from_env': True,
                'frontend_api_key': frontend_key,
            }, options['json'])
            return

        client = MeilisearchConfig.get_client(use_master=True)
        try:
            keys = client.get_keys()
        except Exception as exc:  # 连通性错误
            raise CommandError(f'无法连接 Meilisearch 获取 keys: {exc}') from exc

        # 统一结果为 dict list（pydantic Keys.results 的元素为 Key 对象）
        if isinstance(keys, dict):
            raw_results = keys.get('results', [])
        elif hasattr(keys, 'results'):  # Keys pydantic object（client 0.40.x）
            raw_results = list(keys.results or [])
        else:
            raw_results = []
        results = [_obj_to_dict(r) for r in raw_results]

        target = None
        for k in results:
            name = k.get('name') or ''
            desc = k.get('description') or ''
            if name == 'frontend-search' or desc == 'frontend-search':
                target = k
                break

        if target is None:
            try:
                # 注意：Meilisearch 服务端字段为 camelCase，Python 客户端 0.40.x 直接透传
                created = client.create_key({
                    'name': 'frontend-search',
                    'description': 'frontend-search',
                    'actions': ['search'],
                    'indexes': ['genemaster'],
                    'expiresAt': None,
                })
            except Exception as exc:
                raise CommandError(f'创建 frontend-search key 失败: {exc}') from exc
            target = _obj_to_dict(created)
            self.stdout.write(self.style.SUCCESS('已创建新的 frontend-search key。'))
        else:
            self.stdout.write(self.style.SUCCESS('已复用已有 frontend-search key（未重复创建）。'))

        expires_at = target.get('expiresAt') if target.get('expiresAt') is not None else target.get('expires_at')
        self._print({
            'from_env': False,
            'uid': target.get('uid'),
            'key': target.get('key'),
            'name': target.get('name'),
            'actions': target.get('actions'),
            'indexes': target.get('indexes'),
            'description': target.get('description'),
            'expires_at': expires_at,
        }, options['json'])

        # 一致性检查
        if (target.get('actions') != ['search'] or
                target.get('indexes') != ['genemaster']):
            self.stderr.write(self.style.ERROR(
                'key actions/indexes 不符合规范，请人工确认。'))
            sys.exit(3)

    def _print(self, payload: dict, as_json: bool):
        if as_json:
            import json
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        for k, v in payload.items():
            if isinstance(v, list):
                v = ', '.join(str(x) for x in v)
            self.stdout.write(f'{k:16s}: {v}')
