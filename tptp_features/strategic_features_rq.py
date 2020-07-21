from pathlib import Path
import random
from concurrent import futures
import time
import logging

from rq import Queue
from redis import Redis

import pandas

from .strategic_features import get_problem_features
from .Tptp import Tptp
    
class ProblemFeaturesTimeoutException(Exception):
    def __init__(self, name, timeout, message=None):
        if message is None:
            message = name

        super().__init__(message)
        self.name = name
        self.timeout = timeout

class ProblemFeaturesFailedException(Exception):
    def __init__(self, name, timeout, exc_info, message=None):
        if message is None:
            message = exc_info if exc_info is not None else name

        super().__init__(message)
        self.name = name
        self.timeout = timeout
        self.exc_info = exc_info

def get_problem_features_rq(queue, problem, timeout):
    job = queue.enqueue(
        get_problem_features,
        args=(problem,),
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
                raise ProblemFeaturesFailedException(problem.name, timeout, None)

            return r

        if job.is_failed:
            e = job.exc_info
            job.delete()
            raise ProblemFeaturesFailedException(problem.name, timeout, e)

        trials = min(trials + 1, 512)
        sleep_time = random.uniform(0, 2**trials - 1) * SLEEP_TIME_FACTOR
        sleep_time = min(sleep_time, timeout - time_slept)

    job.delete()
    raise ProblemFeaturesTimeoutException(problem.name, timeout, "Waited for rq, but failed")

MAX_DISPATCHERS = 16
def get_features(tptp, prob_timeout, timeout, dispatchers = MAX_DISPATCHERS):
    redis_conn = Redis()
    queue = Queue(connection=redis_conn)

    data = []
    problems = list(tptp.get_problems({'SPC': 'FOF_.*'}))
    random.shuffle(problems)
    completed_problems = set()
    with futures.ThreadPoolExecutor(max_workers=dispatchers) as executor:
        future_problems = [executor.submit(get_problem_features_rq, queue, p, prob_timeout)
                            for p in problems]
        try:
            for future in futures.as_completed(future_problems, timeout=timeout):
                try:
                    s = future.result()
                except (ProblemFeaturesTimeoutException, ProblemFeaturesFailedException) as e:
                    logging.exception("Timed-out: %s", e.name)
                except Exception as e:
                    logging.exception("Future returned an exception: %s", str(e))
                else:
                    data.append(s)
                    completed_problems.add(s.name)
                    logging.debug("Completed %s", s.name)

        except futures.TimeoutError as e:
            incomplete = [f for f in future_problems if not f.done()]
            logging.exception("Some (%d) problems incomplete because of overall timeout", len(incomplete))
            while incomplete:
                for f in incomplete: f.cancel()
                incomplete = [f for f in incomplete if not f.done()]
            
            logging.debug("Cancelled incomplete problems")

    incomplete = {(p.group, p.name) for p in problems} - completed_problems
    return pandas.DataFrame(data), incomplete

if __name__ == "__main__":
    import sys
    random.seed(0)
    d, _ = get_features(sys.argv[1], 0.1, 3)
    print(d.describe())