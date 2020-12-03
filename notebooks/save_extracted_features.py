#%%
cd ..

#%%
rm -v save_extracted_features.log

#%%
import logging
logger = logging.getLogger()
fh = logging.FileHandler('save_extracted_features.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
ch = logging.StreamHandler()
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

#%%
SINGLE_TIMEOUT = 90
TOTAL_TIMEOUT = 3600*12

#%%
from tptp_features.Tptp import Tptp
import random
random.seed()
import os
os.environ['TPTP'] = '/Users/cm772/Documents/Dev/tptp-parser'
tptp = Tptp('/Users/cm772/Documents/Dev/tptp-parser')
problems_all = list(tptp.get_problems({'SPC': 'FOF_.*'}))
problems = problems_all

#%%
random.shuffle(problems_all)
problems = problems_all #[:30]


#%%
from tptp_features.strategic_features_rq import get_features
data, failed = get_features(problems, SINGLE_TIMEOUT, TOTAL_TIMEOUT)

#%%
import pandas as pd
store = pd.HDFStore('problem_features.h5')
store['features'] = data
store['timeouts'] = pd.Series(dict(single=SINGLE_TIMEOUT, total=TOTAL_TIMEOUT))
store.close()


# %%
