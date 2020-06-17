from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from tptp_v7_0_0_0Lexer import tptp_v7_0_0_0Lexer
from tptp_v7_0_0_0Parser import tptp_v7_0_0_0Parser
from tptp_v7_0_0_0Listener import tptp_v7_0_0_0Listener
from collections import Counter
from pathlib import Path
from random import sample

import numpy as np
import pandas as pd

LEX_FEATURES = """
    Or
    And
    Iff 
    Impl 
    If
    Niff
    Nor
    Nand
    Not
    ForallComb
    TyForall
    Infix_inequality 
    Infix_equality 
    Forall
    ExistsComb
    TyExists
    Exists
    Lambda
    ChoiceComb
    Choice
    DescriptionComb
    Description
    EqComb
    App
    Assignment
    Arrow
    Star
    Plus
    Subtype_sign
    Gentzen_arrow
    Real 
    Signed_real 
    Unsigned_real 
    Rational
    Signed_rational
    Unsigned_rational
    Integer 
    Signed_integer
    Unsigned_integer
    Decimal 
    Positive_decimal 
    Decimal_exponent 
    Decimal_fraction 
    Dot_decimal 
    Exp_integer 
    Signed_exp_integer 
    Unsigned_exp_integer 
""".split()

class StrategicFeaturesListener(tptp_v7_0_0_0Listener):
    def __init__(self):
        super().__init__()

def get_features_index():
    return LEX_FEATURES

def get_problem_features(filename, tptpdir=None):
    input = FileStream(filename)
    lexer = tptp_v7_0_0_0Lexer(input)
    lex_types = dict([(getattr(tptp_v7_0_0_0Lexer, l), l)
                        for l in LEX_FEATURES])
    lex_types_all = lex_types.keys()
    c = Counter([lex_types[t.type] for t in lexer.getAllTokens()
                    if t.type in lex_types_all])
    lexer.reset()
    return pd.Series(c,dtype=np.float64).reindex(get_features_index(), fill_value=0.0)

def get_features(tptpdir):
    data = {}
    problems = list(Path(tptpdir).glob("Problems/*/*.p"))
    for p in sample(problems, 10):
        name = (p.parent.name, p.name)
        print("Trying ", name)
        data[name] = get_problem_features(p)

    print(pd.DataFrame(data).T.describe().T)

if __name__ == "__main__":
    import sys
    get_features(sys.argv[1])