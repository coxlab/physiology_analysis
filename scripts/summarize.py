#!/usr/bin/env python

import logging
import sys

import joblib

import physio

n_jobs = -1


def try_summarize(sn):
    logging.debug("\tprocessing %s" % sn)
    try:
        physio.summary.summarize.summarize_session(sn)
    except Exception as E:
        logging.error("Session %s failed with %s" % \
                (sn, E))


def get_sessions():
    return physio.session.get_sessions()


def summarize(sns, n_jobs):
    joblib.Parallel(n_jobs=n_jobs)(joblib.delayed(try_summarize)(sn) \
            for sn in sns)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    args = sys.argv[1:]
    if len(args):
        summarize(args, n_jobs)
    else:
        summarize(get_sessions(), n_jobs)
