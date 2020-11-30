# %%
cd ..

# %%
from tptp_features.tptp_v7_0_0_0Lexer import tptp_v7_0_0_0Lexer
from tptp_features.tptp_v7_0_0_0Parser import tptp_v7_0_0_0Parser
from tptp_features.tptp_v7_0_0_0Listener import tptp_v7_0_0_0Listener
from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from pprint import pprint

#%%
from tptp_features.Tptp import Tptp
tptp = Tptp("../tptp-parser/")

# %%
import random
random.seed()

problems = list(tptp.get_problems({'SPC': 'FOF_.*'}))
random.shuffle(problems)

#%%
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# %%
class Listener(tptp_v7_0_0_0Listener):
    def __init__(self):
        super().__init__()
        self.includes = []
        self.first = True

    def enterEveryRule(self, ctx):
        if not hasattr(ctx, 'negated_env'):
            if ctx.parentCtx is None:
                ctx.negated_env = False
            else:
                ctx.negated_env = ctx.parentCtx.negated_env

    def enterFof_binary_nonassoc(self, ctx):
        if ctx.binary_connective().Impl():
            logging.debug(f"Flipping context {ctx.negated_env} {ctx.fof_unitary_formula(0).getText()}")
            ctx.fof_unitary_formula(0).negated_env = not ctx.negated_env

    def enterInclude(self, ctx):
        fname = ctx.file_name().Single_quoted().getText().strip("'")
        if ctx.formula_selection():
            formulas = tuple((c.getText() for c in ctx.formula_selection().name_list().name()))
        else:
            formulas = None
        
        self.includes.append((fname, formulas))

# %%
def parse_one(problem):
    lexer = tptp_v7_0_0_0Lexer(FileStream(problem.file))
    stream = CommonTokenStream(lexer)
    parser = tptp_v7_0_0_0Parser(stream)
    tree = parser.tptp_file()
    listener = Listener()
    walker = ParseTreeWalker()
    walker.walk(listener, tree)

    return listener

# %%
l = parse_one(tptp.axioms['SET006+0'])

# %%
class TimeoutException(Exception):
    pass

def parse_problem_timeout(p, timeout):
    import signal

    def signal_handler(signum, frame):
        raise TimeoutSignalException('TIMEOUT')

    signal.signal(signal.SIGALRM, signal_handler)

    signal.alarm(timeout)
    return parse_problem(p)

def parse_problem(p):
    listener = parse_one(p)
    return listener.includes

# %%
l = parse_problem_timeout(problems[3], 3)

# %%
for c, p in enumerate(problems):
    if c % 100 == 0:
        print()

    try:
        formulasel, includes = parse_problem_timeout(p, 1)
        if formulasel:
            print()
            print(p.name, includes, flush=True)
        else:
            print('.', end='')
    except Exception as e:
        print('*', end='')

# %%
from concurrent import futures
with futures.ProcessPoolExecutor(max_workers=4) as executor:
    future_map = {executor.submit(parse_problem, p): p for p in problems}
    for future in futures.as_completed(future_map, timeout=30):
        p = future_map[future]
        try:
            formula_selection, includes = future.result()
            print(p, includes, formula_selection)
        except Exception as e:
            print(p, e)

# %%
p = tptp.problems['KRS180+1']
print(p.name)
lexer = tptp_v7_0_0_0Lexer(FileStream(p.file))
listener = parse(lexer)
print(listener.includes)
print(type(listener.includes[0][0]))
print(dir(listener.includes[0][0]))

# %%
c = listener.includes[0][0]
c.getChild(1)
print(c.symbol)

# %%
from pathlib import Path
a = tptp.find_by_name('Axioms/KRS001+1.ax')
print(a)
# %%
