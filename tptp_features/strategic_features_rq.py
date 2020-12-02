from pathlib import Path
import time
import logging
from enum import Enum, auto

from rq import Queue
from redis import Redis

import pandas

from .strategic_features import get_problem_features

FAILURE_TTL = 3600*48
LOOP_SLEEP_TIME = 1

class ParseOutcome(Enum):
    SUCCESS = auto()
    FAIL = auto()

def get_features_rq(problems, prob_timeout, timeout):
    redis_conn = Redis()
    queue = Queue(connection=redis_conn)

    logging.debug(f"{time.ctime()} Queueing jobs ...")
    jobs = [
        queue.enqueue(
            get_problem_features,
            args=(problem,),
            job_timeout=prob_timeout,
            ttl = timeout,
            failure_ttl=FAILURE_TTL,
        ) for problem in problems
    ]
    logging.debug(f"{time.ctime()} ... done ({len(jobs)}).")

    jobs = {job.id: job for job in jobs}
    my_job_ids = set(jobs.keys())

    finished_reg = queue.finished_job_registry
    failed_reg = queue.failed_job_registry

    def get_active_jobids():
        time.sleep(LOOP_SLEEP_TIME)
        return (
            set(queue.get_job_ids()) |
            set(queue.started_job_registry.get_job_ids()) |
            set(finished_reg.get_job_ids()) |
            set(failed_reg.get_job_ids())
        )

    while get_active_jobids().intersection(my_job_ids):
        for job_id in finished_reg.get_job_ids():
            if job_id not in jobs:
                continue

            job = jobs[job_id]
            job.refresh()
            yield (ParseOutcome.SUCCESS, job)
            finished_reg.remove(job_id, delete_job=True)

        for job_id in failed_reg.get_job_ids():
            if job_id not in jobs:
                continue

            job = jobs[job_id]
            job.refresh()
            yield (ParseOutcome.FAIL, job)
            failed_reg.remove(job_id, delete_job=True)
            # Seems job_ids sometimes change when moving to failed_reg. So
            # failed job might show up twice here. Still not 100% clear.



def get_features(problems, prob_timeout, timeout):
    data = []
    failed = []
    pending = len(problems)

    data = []
    for outcome, job in get_features_rq(problems, prob_timeout, timeout):
        if outcome == ParseOutcome.SUCCESS:
            data.append(job.result)
            pending -= 1
            logging.debug(f"{time.ctime()} Finished {job.args[0].name}, pending {pending}")
        elif outcome == ParseOutcome.FAIL:
            failed.append((job.args[0].name, job.exc_info))
            logging.debug(f"{time.ctime()} Failed {job.args[0].name} with exception {job.exc_info.splitlines()[-1]}")
        else:
            assert False, "Not Reachable"

    n_failed = len(set([n for n,_ in failed]))
    pending -=  n_failed
    if pending > 0:
        logging.debug(f"{time.ctime()} Still {pending} pending jobs ({n_failed} failed) remain but are not in queue. Probably timed out.")
    
    return pandas.DataFrame(data), failed
