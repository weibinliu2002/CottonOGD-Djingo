import os

# 设置R_HOME环境变量
r_home = r'D:\software\R\R-4.5.2'
os.environ['R_HOME'] = r_home

# 在Windows上设置cffi模式为ABI
os.environ['RPY2_CFFI_MODE'] = 'ABI'

import rpy2

# 尝试获取版本信息
try:
    print(f'rpy2 version: {rpy2.__version__}')
except AttributeError:
    print('Could not get rpy2 version')

# 检查转换模块
print('\nChecking conversion modules:')
try:
    from rpy2.robjects import pandas2ri
    print('pandas2ri available')
    print('pandas2ri attributes:', [attr for attr in dir(pandas2ri) if not attr.startswith('_')])
except ImportError as e:
    print(f'pandas2ri import error: {e}')

try:
    from rpy2.robjects.conversion import localconverter
    print('\nlocalconverter available')
except ImportError as e:
    print(f'localconverter import error: {e}')
