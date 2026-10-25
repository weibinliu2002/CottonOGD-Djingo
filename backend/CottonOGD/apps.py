from django.apps import AppConfig


class CottonogdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'CottonOGD'

    def ready(self):
        """Django 启动时注册 signals。"""
        # noqa: F401  导入触发信号注册
        import CottonOGD.signals  # pylint: disable=unused-import,import-outside-toplevel
