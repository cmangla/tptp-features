from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker, ParseTreeListener, ErrorNode, TerminalNode
from .tptp_v7_0_0_0Lexer import tptp_v7_0_0_0Lexer
from .tptp_v7_0_0_0Parser import tptp_v7_0_0_0Parser

from .Tptp import Tptp

from collections import Counter, deque
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
    QUANTIFIER_ALTERNATIONS_TRUE
    QUANTIFIER_RANK
    QUANTIFIERS
    MEAN_FN_ARITY
    MAX_FN_ARITY
""".split()

class QuantifierFeaturesListener(ParseTreeListener):
    def __init__(self):
        super().__init__()
        self.formulae = None
        self.current_formula = None
        self.formula_quantifiers = {}
        self.formula_quantifiers_true = {}
        self.formula_quantifier_rank = {}

    def enterFof_annotated(self, ctx):
        self.formula_quantifiers[self.current_formula] = []
        self.formula_quantifiers_true[self.current_formula] = []

    def exitFof_annotated(self, ctx):
        assert self.current_formula == ctx.name().getText()
        self.formula_quantifier_rank[self.current_formula] = ctx.fof_formula().quantifier_rank
        self.current_formula = None

    def enterFof_quantifier(self, ctx):
        self.formula_quantifiers[self.current_formula].append(ctx.getText())
        assert ctx.Forall() is None or ctx.Exists() is None
        qf = ctx.Forall() is None # qf is True if quantifier is Exists symbol
        if ctx.negated_env:
            qf = not qf

        self.formula_quantifiers_true[self.current_formula].append(qf)

    def enterEveryRule(self, ctx):
        if not hasattr(ctx, 'negated_env'):
            if ctx.parentCtx is None:
                ctx.negated_env = False
            else:
                ctx.negated_env = ctx.parentCtx.negated_env

    def exitFof_quantified_formula(self, ctx):
        ctx.quantifier_rank = 1 + getattr(
            ctx.fof_unitary_formula(), 'quantifier_rank', 0
            )

    def exitEveryRule(self, ctx):
        if not hasattr(ctx, 'quantifier_rank'):
            ctx.quantifier_rank = max(
                (getattr(c, 'quantifier_rank', 0) for c in ctx.getChildren())
            )

    def enterFof_binary_nonassoc(self, ctx):
        connective = ctx.binary_connective()
        if connective.Impl():
            ctx.fof_unitary_formula(0).negated_env = not ctx.negated_env
        elif connective.If():
            ctx.fof_unitary_formula(1).negated_env = not ctx.negated_env
        elif connective.Nor() or connective.Nand():
            ctx.fof_unitary_formula(0).negated_env = not ctx.negated_env
            ctx.fof_unitary_formula(1).negated_env = not ctx.negated_env
        elif connective.Iff() or connective.Niff():
            ctx.num_quantifiers = len(self.formula_quantifiers_true[self.current_formula])
        else:
            assert False, 'UNREACHABLE: unknown connective'

    def exitFof_binary_nonassoc(self, ctx):
        connective = ctx.binary_connective()
        if connective.Iff() or connective.Niff():
            quantifiers = self.formula_quantifiers_true[self.current_formula][ctx.num_quantifiers:]
            quantifiers = [not q for q in quantifiers]
            self.formula_quantifiers_true[self.current_formula].extend(quantifiers)

    def enterFof_unary_formula(self, ctx):
        if ctx.unary_connective() and ctx.unary_connective().Not():
            ctx.fof_unitary_formula().negated_env = not ctx.negated_env

    def enterFof_infix_unary(self, ctx):
        for i in [0, 1]:
            ctx.fof_term(i).negated_env = not ctx.negated_env


    def get_features(self, formulae=None):
        if formulae is None:
            formulae = self.formulae
        else:
            formulae = set(formulae)

        features = Counter()
        quantifier_alternations = 0
        quantifier_alternations_true = 0
        quantifier_counts = 0

        for f in formulae:
            q = self.formula_quantifiers[f]
            if q:
                logging.debug(f"Quantifiers[{f}] = {','.join(q)}")

        for f in formulae:
            q = self.formula_quantifiers_true[f]
            if q:
                q = ['?' if i else '!' for i in q]
                logging.debug(f"Quantifiers_true[{f}] = {','.join(q)}")

        for f in formulae:
            r = self.formula_quantifier_rank[f]
            logging.debug(f"Quantifier_rank[{f}] = {r}")

        for formula in formulae:
            q = self.formula_quantifiers[formula]
            quantifier_counts += len(q)
            for i, j in zip(q, q[1:]):
                quantifier_alternations += 1 if i != j else 0

            q = self.formula_quantifiers_true[formula]
            for i, j in zip(q, q[1:]):
                quantifier_alternations_true += 1 if i != j else 0

        quantifier_rank = max((self.formula_quantifier_rank[f] for f in formulae)) if formulae else 0
        features.update({'QUANTIFIER_ALTERNATIONS': quantifier_alternations})
        features.update({'QUANTIFIER_ALTERNATIONS_TRUE': quantifier_alternations_true})
        features.update({'QUANTIFIER_RANK': quantifier_rank})
        features.update({'QUANTIFIERS': quantifier_counts})
        return features

class FunctionsFeaturesListener(ParseTreeListener):
    def __init__(self):
        super().__init__()
        self.formulae = None
        self.current_formula = None
        self.formula_functions = {} # formula -> set(functions)
        self.functions = {} # function -> arity

    def enterFof_annotated(self, ctx):
        self.formula_functions[self.current_formula] = set()

    def exitFof_annotated(self, ctx):
        assert self.current_formula == ctx.name().getText()

    def enterFof_plain_term(self, ctx):
        if ctx.constant():
            return

        fn_name = ctx.functor().getText()
        self.formula_functions[self.current_formula].add(fn_name)

        if fn_name in self.functions:
            return

        fn_args = ctx.fof_arguments().fof_term()
        self.functions[fn_name] = len(fn_args)

    def get_features(self, formulae=None):
        if formulae is None:
            formulae = self.formulae
        else:
            formulae = set(formulae)

        arities = [
            self.functions[function]
                for formula in formulae
                for function in self.formula_functions[formula]
        ]
        return Counter(
            {
                'MEAN_FN_ARITY': sum(arities)/len(arities) if arities else 0,
                'MAX_FN_ARITY': max(arities) if arities else 0
            }
        )

class HelperFeaturesListener(ParseTreeListener):
    """
    Helps all other listeners in the list of listeners, by setting useful
    variables in them. Puts itself at the beginning of list of listeners, and so
    is called first on entry, and last on exit. Used by MultiFeatureListener .
    """

    def __init__(self, listeners):
        self.listeners = listeners
        self.listeners.insert(0, self)
        self.current_formula = None
        self.formulae = set()
        for l in listeners[1:]:
            l.formulae = self.formulae

    def _update_listeners(self):
        assert self.listeners[0] is self
        for l in self.listeners[1:]:
            l.current_formula = self.current_formula

    def enterFof_annotated(self, ctx):
        assert self.current_formula is None
        self.current_formula = ctx.name().getText()
        assert self.current_formula not in self.formulae
        self.formulae.add(self.current_formula)
        self._update_listeners()

    def exitFof_annotated(self, ctx):
        assert self.current_formula == ctx.name().getText()
        self.current_formula = None
        self._update_listeners()
    
    def get_features(self, formulae=None):
        logging.debug("for features, using formulae: " + ",".join(
            formulae if formulae else ['ALL']
        ))
        if formulae:
            formulae = set(formulae)
            assert formulae <= self.formulae, f"{formulae} should be subset of {self.formulae}"

        return Counter()

class MultiFeatureListener(ParseTreeListener):
    """
    Dispatch to a list of listeners that can generate features
    """

    def __init__(self, listeners):
        self.listeners = listeners
        HelperFeaturesListener(self.listeners)
        self.includes = []

    def enterInclude(self, ctx):
        fname = ctx.file_name().Single_quoted().getText().strip("'")
        if ctx.formula_selection():
            formulas = tuple((c.getText() for c in ctx.formula_selection().name_list().name()))
        else:
            formulas = None

        self.includes.append((fname, formulas))

    def visitTerminal(self, node):
        for l in self.listeners:
            l.visitTerminal(node)

    def visitErrorNode(self, node):
        for l in self.listeners:
            l.visitErrorNode(node)

    def enterEveryRule(self, ctx):
        for l in self.listeners:
            l.enterEveryRule(ctx)
            ctx.enterRule(l)

    def exitEveryRule(self, ctx):
        for l in reversed(self.listeners):
            ctx.exitRule(l)
            l.exitEveryRule(ctx)

    def get_features(self, formulae=None):
        features = Counter()
        for l in self.listeners:
            features.update(l.get_features(formulae))

        return features

def get_features_index():
    return LEX_FEATURES + PARSE_FEATURES

class ParseTreeWalkerIterative(ParseTreeWalker):

    def walk(self, listener, t):
        stack = deque([(False, t)]) # [(a: Bool, n: ParseTree), ...] ; a is True if node needs exiting
        while stack:
            needsExit, t = stack.pop()
            if needsExit:
                self.exitRule(listener, t)
            elif isinstance(t, ErrorNode):
                listener.visitErrorNode(t)
            elif isinstance(t, TerminalNode):
                listener.visitTerminal(t)
            else:
                self.enterRule(listener, t)
                stack.append((True, t)) # For exit of this rule
                if not t.children:
                    continue

                stack.extend(
                    ((False, i) for i in reversed(t.children))
                )


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
    listener = MultiFeatureListener([
        QuantifierFeaturesListener(),
        FunctionsFeaturesListener()
    ])
    walker = ParseTreeWalkerIterative()
    walker.walk(listener, tree)

    features.update(listener.get_features(formulae))
    includes = [(tptp.find_by_filename(i), f) for i, f in listener.includes]
    return features, includes

def parse_with_includes(problem):
    tptp = Tptp(problem.tptp)
    includes = deque([(problem, None)])
    features = Counter()
    while includes:
        prob, formulae = includes.popleft()
        logging.debug('Including {}, {}'.format(prob.name, formulae))
        prob_features, prob_includes = parse_one(tptp, prob, formulae)
        includes.extend(prob_includes)
        features.update(prob_features)
        
    return features

def get_problem_features(problem):
    c = parse_with_includes(problem)
    return pd.Series(c, dtype=np.float64, name=(problem.group, problem.name)).reindex(
            get_features_index(), fill_value=0.0)

