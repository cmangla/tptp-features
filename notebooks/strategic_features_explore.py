#%%
cd ..

#%%
from tptp_features.Tptp import Tptp
from tptp_features.strategic_features import get_problem_features, parse_with_includes, parse_one
tptp = Tptp("../tptp-parser/")

#%%
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# %%
#
f, i = parse_one(tptp, tptp.axioms['SET005+0'])

# %%
# Has implies, which causes quantifier negation!
f = parse_with_includes(tptp.axioms['SET007+1'])

#%%
# NUM303+1

#include('Axioms/NUM005+0.ax').
#include('Axioms/NUM005+1.ax').
#include('Axioms/NUM005+2.ax').
#
#fof(n31_not_n12,conjecture,
#    (  n31 != n21 )).

f = get_problem_features(tptp.problems['NUM303+1'])

# %%
# Gave an error once:  ValueError: max() arg is an empty sequence
f = parse_with_includes(tptp.problems['GEO160+1'])

#%%
f = get_problem_features(tptp.problems['PUZ069+2'])

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

# %%
# Problems/LAT/LAT300+2.p
# Includes cannot be found
a = tptp.find_by_filename('Axioms/SET007/SET007+0.ax')
f = get_problem_features(tptp.problems['LAT300+2'])

# %%
import pickle
from pathlib import Path
problems = list(tptp.get_problems({'SPC': 'FOF_.*'}))
with Path('problems.pickle').open(mode='wb') as f:
    pickle.dump(problems, f, protocol=pickle.HIGHEST_PROTOCOL)

# %%
import pickle
from pathlib import Path
with Path('problems.pickle').open(mode='rb') as f:
    problems = pickle.load(f)

# %%
import random
random.seed()
random.shuffle(problems)

#%%
for p in problems:
    print('----')
    print(p.name)
    f = get_problem_features(p)
    input()

# %%
print(f)