import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 测试R初始化
try:
    # 设置R_HOME环境变量
    r_home = r'D:\software\R\R-4.5.2'
    if os.path.exists(r_home):
        os.environ['R_HOME'] = r_home
        logger.info(f'Set R_HOME to: {r_home}')
    else:
        logger.warning(f'R installation path not found: {r_home}')
    
    # 在Windows上设置cffi模式为ABI
    os.environ['RPY2_CFFI_MODE'] = 'ABI'
    logger.info('Set RPY2_CFFI_MODE to ABI for Windows compatibility')
    
    import rpy2
    logger.info('rpy2 module imported successfully')
    
    # 尝试初始化R
    import rpy2.rinterface as rinterface
    rinterface.initr()
    logger.info('R initialization successful!')
    
    # 测试R功能
    import rpy2.robjects as robjects
    result = robjects.r('1 + 1')
    logger.info(f'R test result: {result[0]}')
    
except Exception as e:
    logger.error(f'Error: {str(e)}')
