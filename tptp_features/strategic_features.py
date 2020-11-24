from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from .tptp_v7_0_0_0Lexer import tptp_v7_0_0_0Lexer
from .tptp_v7_0_0_0Parser import tptp_v7_0_0_0Parser
from .tptp_v7_0_0_0Listener import tptp_v7_0_0_0Listener

from .Tptp import Tptp

from collections import Counter
import pandas as pd
import numpy  as np

import logging

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

PARSE_FEATURES = """
    QUANTIFIER_ALTERNATIONS
    QUANTIFIERS
""".split()

class StrategicFeaturesListener(tptp_v7_0_0_0Listener):
    def __init__(self):
        super().__init__()
        self.formulae = set()
        self.current_formula = None
        self.formula_quantifiers = {}
        self.includes = []

    def enterInclude(self, ctx):
        fname = ctx.file_name().Single_quoted().getText().strip("'")
        if ctx.formula_selection():
            formulas = tuple((c.getText() for c in ctx.formula_selection().name_list().name()))
        else:
            formulas = None

        self.includes.append((fname, formulas))

    def enterFof_annotated(self, ctx):
        assert self.current_formula is None
        self.current_formula = ctx.name().getText()
        assert self.current_formula not in self.formulae
        self.formulae.add(self.current_formula)

        self.formula_quantifiers[self.current_formula] = []

    def exitFof_annotated(self, ctx):
        assert self.current_formula == ctx.name().getText()
        logging.debug("QUANTIFIERS for {}: {}".format(
            self.current_formula,
            ','.join(self.formula_quantifiers[self.current_formula])
            ))
        self.current_formula = None

    def enterFof_quantifier(self, ctx):
        self.formula_quantifiers[self.current_formula].append(ctx.getText())

    def enterFof_formula(self, ctx):
        # logging.debug(dir(ctx))
        # logging.debug(ctx.getText())
        # logging.debug(ctx.fof_logic_formula().getText())
        # logging.debug(ctx.fof_sequent())
        pass

    def get_features(self, formulae=None):
        if formulae is None:
            formulae = self.formulae
        else:
            formulae = set(formulae)
            assert(formulae <= self.formulae)
            
        logging.debug("for features, using formulae: " + ",".join(formulae))
        features = Counter()
        quantifier_alternations = 0
        quantifier_counts = 0
        for formula in formulae:
            q = self.formula_quantifiers[formula]
            quantifier_counts += len(q)
            for i, j in zip(q, q[1:]):
                quantifier_alternations += 1 if i != j else 0

        features.update({'QUANTIFIER_ALTERNATIONS': quantifier_alternations})
        features.update({'QUANTIFIERS': quantifier_counts})
        return features


def get_features_index():
    return LEX_FEATURES + PARSE_FEATURES

def parse_one(tptp, problem, formulae=None):
    infile = FileStream(problem.file)
    lexer = tptp_v7_0_0_0Lexer(infile)
    lex_types = dict([(getattr(tptp_v7_0_0_0Lexer, l), l)
                        for l in LEX_FEATURES])
    lex_types_all = lex_types.keys()
    features = Counter([lex_types[t.type] for t in lexer.getAllTokens()
                    if t.type in lex_types_all])
    lexer.reset()

    stream = CommonTokenStream(lexer)
    parser = tptp_v7_0_0_0Parser(stream)
    tree = parser.tptp_file()
    listener = StrategicFeaturesListener()
    walker = ParseTreeWalker()
    walker.walk(listener, tree)

    features.update(listener.get_features(formulae))
    includes = [(tptp.find_by_filename(i), f) for i, f in listener.includes]
    return features, includes

def parse_with_includes(problem):
    tptp = Tptp(problem.tptp)
    includes = [(problem, None)]
    features = Counter()
    while includes:
        prob, formulae = includes.pop(0)
        logging.debug('Including {}, {}'.format(prob.name, formulae))
        prob_features, prob_includes = parse_one(tptp, prob, formulae)
        includes.extend(prob_includes)
        features.update(prob_features)
        
    return features

def get_problem_features(problem):
    c = parse_with_includes(problem)
    return pd.Series(c, dtype=np.float64, name=(problem.group, problem.name)).reindex(
            get_features_index(), fill_value=0.0)

