from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.core.cache import cache
import os
import shutil
import logging
logger = logging.getLogger(__name__)


class _CacheSessionMap:
    """
    uuid -> {file_type: file_path} 的会话映射，落 Redis（settings.CACHES）。

    之前的进程内 dict 在 daphne 重启后全部丢失、多 worker 下也不共享，
    导致各接口 `uuid not in UuidManager.uuid_storage` 误判 400。
    改为跨进程/跨重启的缓存存储；key 前缀 uuid_session:，TTL 24 小时。
    """

    PREFIX = 'uuid_session:'
    TTL = 60 * 60 * 24

    def _key(self, uuid):
        return f'{self.PREFIX}{uuid}'

    def __contains__(self, uuid):
        return cache.get(self._key(uuid)) is not None

    def __getitem__(self, uuid):
        value = cache.get(self._key(uuid))
        if value is None:
            raise KeyError(uuid)
        return value

    def __setitem__(self, uuid, value):
        cache.set(self._key(uuid), value, self.TTL)

    def get(self, uuid, default=None):
        value = cache.get(self._key(uuid))
        return default if value is None else value

    def pop(self, uuid, default=None):
        value = self.get(uuid, default)
        cache.delete(self._key(uuid))
        return value


class UuidManager:
    uuid_storage = _CacheSessionMap()

    @classmethod
    def add_entry(cls, uuid, file_type, file_path):
        """添加 UUID 相关的文件路径及配置信息"""
        entry = cache.get(f'uuid_session:{uuid}')
        if entry is None:
            entry = {}  # 创建新的 UUID 条目
        if file_type in entry and entry[file_type]:
            existing_file_path = entry[file_type]
            if os.path.exists(existing_file_path):  # 删除旧文件
                os.remove(existing_file_path)
                logger.debug(f"The file {existing_file_path} exists, delete the file")

        entry[file_type] = file_path  # 记录文件路径及配置
        cache.set(f'uuid_session:{uuid}', entry, _CacheSessionMap.TTL)

    @classmethod
    def get_files_for_uuid(cls, uuid):
        """根据 UUID 获取关联的文件和配置信息"""
        return cls.uuid_storage.get(uuid, {})  # 返回 UUID 对应的文件信息

    @classmethod
    def delete_uuid_entry(cls, uuid):
        """删除 UUID 及其关联的所有文件信息"""
        cls.uuid_storage.pop(uuid)  # 清除会话条目（Redis）
        uuid_path = f'{settings.TEMP_DIR}/{uuid}'
        try:
            if os.path.exists(uuid_path):
                shutil.rmtree(uuid_path)
            else:
                logger.debug(f"Directory {uuid_path} does not exist")
        except Exception as e:
            logger.error(f"Failed to delete directory {uuid_path}: {str(e)}")
            return Response({'error': f'Failed to delete directory: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def login(request):
    """
    建立会话：服务端生成 uuid，签发 token（Redis，7 天），并种 HttpOnly cookie。
    前端取返回体中的 token 放 Authorization: Bearer；同站场景 cookie 自动生效。
    """
    import uuid as uuid_lib

    from CottonOGD.auth import COOKIE_NAME, issue_token

    uuid = str(uuid_lib.uuid4())
    token = issue_token(uuid)
    UuidManager.add_entry(uuid, 'uuid', uuid)
    uuid_path = f'{settings.TEMP_DIR}/{uuid}'
    try:
        os.makedirs(uuid_path, exist_ok=True)
    except Exception as e:
        return Response({'error': f'Failed to create directory: {str(e)}'}, status=status.HTTP_403_FORBIDDEN)

    response = Response({'uuid': uuid, 'token': token}, status=status.HTTP_200_OK)
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        samesite='Lax',
        secure=request.is_secure(),
    )
    return response

@api_view(['POST'])
def logout(request):
    # 使 token 失效（header/cookie 任一通道）并删除会话
    from CottonOGD.auth import COOKIE_NAME, extract_token, revoke_token

    token = extract_token(request) or request.data.get('token')
    if token:
        revoke_token(token)
    uuid = request.data.get('uuid') or request.headers.get('uuid')
    if uuid:
        UuidManager.delete_uuid_entry(uuid)

    response = Response(status=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(COOKIE_NAME)
    return response