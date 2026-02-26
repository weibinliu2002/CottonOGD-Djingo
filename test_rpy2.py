import os
os.environ['R_HOME'] = r'D:\Program Files\R\R-4.5.2'

import rpy2.situation as rpy2_situation
rpy2_situation.R_HOME = r'D:\Program Files\R\R-4.5.2'

import rpy2.rinterface as rinterface
rinterface.initr()
print('R initialization successful!')
