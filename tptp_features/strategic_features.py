from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from .tptp_v7_0_0_0Lexer import tptp_v7_0_0_0Lexer
from .tptp_v7_0_0_0Parser import tptp_v7_0_0_0Parser
from .tptp_v7_0_0_0Listener import tptp_v7_0_0_0Listener

from collections import Counter
from pathlib import Path
import random
from concurrent import futures
import time
import logging

from rq import Queue
from redis import Redis

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
    return pd.Series(c, dtype=np.float64, name=filename).reindex(
            get_features_index(), fill_value=0.0)
    
class ProblemFeaturesTimeoutException(Exception):
    def __init__(self, filename, timeout, message=None):
        if message is None:
            message = filename

        super().__init__(message)
        self.filename = filename
        self.timeout = timeout

class ProblemFeaturesFailedException(Exception):
    def __init__(self, filename, timeout, exc_info, message=None):
        if message is None:
            message = exc_info if exc_info is not None else filename

        super().__init__(message)
        self.filename = filename
        self.timeout = timeout
        self.exc_info = exc_info

def get_problem_features_rq(queue, filename, timeout):
    job = queue.enqueue(
        get_problem_features,
        args=(filename,),
        job_timeout=timeout,
        failure_ttl=10
        )

    SLEEP_TIME_FACTOR = 0.1
    SLEEP_TIME_INITIAL = 0.001

    time_slept = 0
    sleep_time = SLEEP_TIME_INITIAL
    trials = 0
    while time_slept < timeout:
        time.sleep(sleep_time)
        time_slept += sleep_time

        if job.is_finished:
            r = job.result
            job.delete()
            if r is None:
                raise ProblemFeaturesFailedException(filename, timeout)

            return r

        if job.is_failed:
            e = job.exc_info
            job.delete()
            raise ProblemFeaturesFailedException(filename, timeout, e)

        trials = min(trials + 1, 512)
        sleep_time = random.uniform(0, 2**trials - 1) * SLEEP_TIME_FACTOR
        sleep_time = min(sleep_time, timeout - time_slept)

    job.delete()
    raise ProblemFeaturesTimeoutException(filename, timeout, "Waited for rq, but failed")

MAX_DISPATCHERS = 8
def get_features(tptpdir, prob_timeout, timeout, dispatchers = MAX_DISPATCHERS):
    redis_conn = Redis()
    q = Queue(connection=redis_conn)

    data = {}
    problems = list(Path(tptpdir).glob("Problems/*/*.p"))
    random.shuffle(problems)
    completed_problems = set()
    with futures.ThreadPoolExecutor(max_workers=dispatchers) as executor:
        future_problems = [executor.submit(get_problem_features_rq, q, p, prob_timeout)
                            for p in problems]
        try:
            for future in futures.as_completed(future_problems, timeout=timeout):
                try:
                    s = future.result()
                except ProblemFeaturesTimeoutException as e:
                    logging.exception("Timed-out: %s", e.filename)
                except Exception as e:
                    logging.exception("Future returned an exception: %s", str(e))
                else:
                    p = s.name
                    data[(p.parent.name, p.name)] = s
                    completed_problems.add(p)

        except futures.TimeoutError as e:
            incomplete = [f for f in future_problems if not f.done()]
            logging.exception("Some (%d) problems incomplete because of overall timeout", len(incomplete))
            while incomplete:
                for f in incomplete: f.cancel()
                incomplete = [f for f in incomplete if not f.done()]

    incomplete = set(problems) - completed_problems
    return pd.DataFrame(data).T, incomplete

if __name__ == "__main__":
    import sys
    random.seed(0)
    d, _ = get_features(sys.argv[1], 0.1, 3)
    print(d.describe())
