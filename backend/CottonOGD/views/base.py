from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os
import shutil
import logging
logger = logging.getLogger(__name__)

class UuidManager:
    uuid_storage = {}
    @classmethod
    def add_entry(cls, uuid, file_type, file_path):
        """添加 UUID 相关的文件路径及配置信息"""
        if uuid not in cls.uuid_storage:
            cls.uuid_storage[uuid] = {}  # 创建新的 UUID 条目
        if file_type in cls.uuid_storage[uuid] and cls.uuid_storage[uuid][file_type]:
            existing_file_path = cls.uuid_storage[uuid][file_type]
            if os.path.exists(existing_file_path):  # 确保文件存在
                os.remove(existing_file_path)  # 删除旧文件
                logger.debug(f"The file {existing_file_path} exists, delete the file")

        cls.uuid_storage[uuid][file_type] = file_path  # 记录文件路径及配置

    @classmethod
    def get_files_for_uuid(cls, uuid):
        """根据 UUID 获取关联的文件和配置信息"""
        return cls.uuid_storage.get(uuid, {})  # 返回 UUID 对应的文件信息

    @classmethod
    def delete_uuid_entry(cls, uuid):
        """删除 UUID 及其关联的所有文件信息"""
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
    # 从多个来源获取 UUID：请求体、查询参数、请求头
    uuid = request.headers.get('uuid')
    logger.debug(f"login uuid: {uuid}")
    
    if not uuid:
        return Response({'error': 'uuid is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    UuidManager.add_entry(uuid, 'uuid', uuid)
    uuid_path = f'{settings.TEMP_DIR}/{uuid}'
    try:
        os.makedirs(uuid_path, exist_ok=True)
    except Exception as e:
        return Response({'error': f'Failed to create directory: {str(e)}'}, status=status.HTTP_403_FORBIDDEN)
    return Response({'message': 'Successfully connected!'}, status=status.HTTP_200_OK)

@api_view(['POST'])
def logout(request):
    uuid = request.data.get('uuid')
    # 删除uuid对应的条目
    UuidManager.delete_uuid_entry(uuid)

    return Response(status=status.HTTP_204_NO_CONTENT)