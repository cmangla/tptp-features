#%%
cd ..

#%%
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

#%%
SINGLE_TIMEOUT = 20
TOTAL_TIMEOUT = 60

#%%
from tptp_features.Tptp import Tptp
import random
random.seed()
tptp = Tptp("../tptp-parser/")
problems = list(tptp.get_problems({'SPC': 'FOF_.*'}))
random.shuffle(problems)
#problems = problems[:30]

#%%
from tptp_features.strategic_features_rq_pure import get_features
data, incomplete = get_features(problems, SINGLE_TIMEOUT, TOTAL_TIMEOUT)

#%%
import pandas as pd
incomplete = pd.Series(list(incomplete))
incomplete.describe()

#%%
store = pd.HDFStore('problem_features.h5')
store['features'] = data
store['incomplete'] = incomplete
store['timeouts'] = pd.Series(dict(single=SINGLE_TIMEOUT, total=TOTAL_TIMEOUT))
store.close()