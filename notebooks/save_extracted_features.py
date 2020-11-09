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
tptp = Tptp("../tptp-parser/")

#%%
from tptp_features.strategic_features_rq import get_features
data, incomplete = get_features(tptp, SINGLE_TIMEOUT, TOTAL_TIMEOUT)

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