"""测试专用 settings：用 SQLite 内存库替代 MySQL（CI/本地无建库权限时）。

运行：DJANGO_SETTINGS_MODULE=mysite.test_settings python manage.py test ...
"""
from mysite.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
    'server': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

# 测试不依赖真实迁移（原迁移针对 MySQL，且本环境无建库权限）；
# PPI 测试全部 mock DB/网络访问，故跳过迁移。
MIGRATION_MODULES = {
    'CottonOGD': None,
}

