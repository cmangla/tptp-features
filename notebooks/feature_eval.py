# %%
cd ..

# %%
import json
from itertools import permutations
import numpy as np
np.seterr(all='raise')
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import pairwise_kernels
from sklearn.decomposition import PCA
from pprint import pprint
from minepy import MINE
from scipy.stats import pearsonr
from collections import namedtuple
import sys
import pandas as pd

# %%
NUM_STRATEGIES = 5
MINIMUM_SCORE = 0.0000001

# %%
# problem_features = None # theorem -> features
# with open("problem_features.json", 'r') as f:
#     problem_features = json.load(f) # contains all problems

# problems = tuple(problem_features.keys())
# problem_features = [problem_features[i] for i in problems]
# #problem_features = normalize(problem_features)
# problem_features = {p: problem_features[i] for i, p in enumerate(problems)}

# features = ['fof_term', 'fof_plain_term', 'ATOMIC_WORD', 'fof_unitary_formula', 'fof_unit_formula', 'fof_function_term', 'UPPER_WORD', 'variable', 'fof_atomic_formula', 'fof_plain_atomic_formula', 'fof_logic_formula', 'fof_binary_formula', 'NONASSOC_CONNECTIVE', 'fof_binary_nonassoc', '<=>', 'fof_and_formula', 'fof_or_formula', 'fof_unary_formula', 'UNARY_CONNECTIVE', 'LOWER_WORD', 'fof_binary_assoc', 'tptp_input', 'annotated_formula', 'fof_annotated', 'formula_role', 'NAME', 'fof_formula', 'FOF_QUANTIFIER', 'fof_quantified_formula', '!', '=>', 'fof_defined_atomic_formula', 'fof_defined_plain_formula', 'fof_defined_plain_term', 'fof_defined_infix_formula', 'INFIX_INEQUALITY', 'fof_infix_unary', 'SINGLE_QUOTED', 'file_name', 'include', '?', '<~>', 'general_term', 'general_data', 'general_terms', 'general_function', 'annotations', 'source', 'number', 'REAL', '<=', 'ESCAPED_STRING', 'distinct_object', 'tptp_file', 'defined_term', 'fof_defined_term', 'formula_data', 'SIGNED_INT', 'formula_selection', 'useful_info', '~&', '~<|>']

# %%
with pd.HDFStore('data/problem_features.h5') as store:
    problem_features = store['features']

features = problem_features.columns

# %%
strategy_evaluation_training_data = {}
with open('data/strategy_evaluation_training_data.json', 'r') as f:
    strategy_evaluation_training_data_json = json.load(f)
    for theorem, strategy_results in strategy_evaluation_training_data_json.items():
        theorem = theorem.split('/')
        theorem = "/".join((theorem[1], '.'.join((theorem[2].split('.')[:-1]))))
        strategy_evaluation_training_data[theorem] = strategy_results

# %%
D = []
for theorem, strategy_results in strategy_evaluation_training_data.items():
    scores = [(1.0/strategy_results[str(i)][1]) if strategy_results[str(i)][0] else MINIMUM_SCORE for i in range(NUM_STRATEGIES)]
    k = tuple(theorem.split('/'))
    try:
        D.append((problem_features.loc[[k]].iloc[0].tolist(), scores))
    except Exception as e:
        print(e, type(e))
        pass

# %%
DFX = np.array([d[0] for d in D])
DFY = [np.array([d[1][i] for d in D]) for i in range(5)]

mine = MINE()
mics = []
for j in range(NUM_STRATEGIES):
    for i in range(DFX.shape[1]):
        mine.compute_score(DFX[:, i],DFY[j])
        mics.append((features[i], j, mine.mic()))
    #mics.append((features[i], mine.mic(), abs(pearsonr(DFX[:, i], DFY[0])[0])))


# %%
import csv
with open('data/scores.csv', mode='w') as f:
    cw = csv.writer(f)
    cw.writerow(['x', 'y', 'score'])
    for m in mics:
        cw.writerow([str(v) for v in m])
        
# %%
print("x,y,score")
for m in mics:
    print(",".join([str(v) for v in m]))

print()

# %%
# install.packages("ggplot2")
# d <- read.csv("d", header = TRUE)
# library("ggplot2")
# ggplot(d, aes(x=x,y=y,size=score,label=sprintf("%0.2f", round(score, digits = 2)))) + geom_point(shape = 21, fill = "white") + theme(axis.text.x = element_text(angle = 90, hjust = 1)) + geom_text(size=1)
# ggplot(d, aes(reorder(x, score, FUN=median),score,label=y)) + geom_point(shape = 21, fill = "white") + geom_text(size=1) + coord_flip()
# ggplot(d, aes(reorder(x, score, FUN=mean),score)) + geom_boxplot(outlier.shape = NA) + geom_jitter(size=.5,color="red",width=0.1) + coord_flip()

# %%
xavg = {}
for f, _, m in mics:
    xavg[f] = xavg.get(f,0.0) + m

xavg = sorted([(k, v/5.0) for k, v in xavg.iteritems()], key=lambda x: x[1], reverse=True)
pprint(xavg)

