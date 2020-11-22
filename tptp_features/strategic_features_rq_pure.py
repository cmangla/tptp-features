from pathlib import Path
import time
import logging

from rq import Queue
from redis import Redis

import pandas

from .strategic_features import get_problem_features

FAILURE_TTL = 3600*48
LOOP_SLEEP_TIME = 1

def get_features(problems, prob_timeout, timeout):
    redis_conn = Redis()
    queue = Queue(connection=redis_conn)

    logging.debug("Queueing jobs ...")
    jobs = [
        queue.enqueue(
            get_problem_features,
            args=(problem,),
            job_timeout=prob_timeout,
            ttl = timeout,
            failure_ttl=FAILURE_TTL,
        ) for problem in problems
    ]
    logging.debug(f"... done({len(jobs)})")
    pending = len(jobs)
    jobs = {job.id: job for job in jobs}

    started_reg = queue.started_job_registry
    finished_reg = queue.finished_job_registry
    failed_reg = queue.failed_job_registry
    incomplete = set()

    data = []
    while pending > 0 and started_reg.count > 0:
        time.sleep(LOOP_SLEEP_TIME)
        for job_id in finished_reg.get_job_ids():
            if job_id not in jobs:
                continue

            job = jobs[job_id]
            data.append(job.result)
            finished_reg.remove(job_id, delete_job=True)
            pending -= 1
            logging.debug(f"Finished {job.args[0].name}")

        for job_id in failed_reg.get_job_ids():
            if job_id not in jobs:
                continue

            job = jobs[job_id]
            logging.debug(f"Failed {job.args[0].name} with exception {job.exc_info}")
            p = job.args[0]
            incomplete.add((p.group, p.name))
            failed_reg.remove(job_id, delete_job=True)
            pending -= 1

    if pending > 0:
        logging.debug(f"Still {pending} pending jobs remain but are not in queue. Probably timed out.")
    
    return pandas.DataFrame(data), incomplete