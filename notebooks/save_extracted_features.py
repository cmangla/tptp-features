#%%
cd ..

#%%
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

#%%
SINGLE_TIMEOUT = 10
TOTAL_TIMEOUT = 20

#%%
from tptp_features.Tptp import Tptp
import random
random.seed()
import os
os.environ['TPTP'] = '/Users/cm772/Documents/Dev/tptp-parser'
tptp = Tptp('/Users/cm772/Documents/Dev/tptp-parser')
problems = list(tptp.get_problems({'SPC': 'FOF_.*'}))

#%%
random.shuffle(problems)
problems = problems[:30]

#%%
from tptp_features.strategic_features_rq_pure import get_features
data, failed = get_features(problems, SINGLE_TIMEOUT, TOTAL_TIMEOUT)

#%%
store = pd.HDFStore('problem_features.h5')
store['features'] = data
store['incomplete'] = incomplete
store['timeouts'] = pd.Series(dict(single=SINGLE_TIMEOUT, total=TOTAL_TIMEOUT))
store.close()