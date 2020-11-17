#%%
cd ..

#%%
from tptp_features.Tptp import Tptp
from tptp_features.strategic_features import get_problem_features
tptp = Tptp("../tptp-parser/")
problems = list(tptp.get_problems({'SPC': 'FOF_.*'}))

#%%
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

#%%

f = get_problem_features(tptp.problems['SET995+1'])

# %%
# This has includes
f = get_problem_features(tptp.problems['SET199+4'])

# %%
# This produces an error in the parser
f = get_problem_features(tptp.problems['KRS180+1'])

# %%
# This has formula selection
f = get_problem_features(tptp.problems['SYN000+2'])

#%%
import random
random.seed()
random.shuffle(problems)
for p in problems:
    print(p.name)
    f = get_problem_features(p)
    input()

# %%
print(f)