#!/usr/bin/env python

import logging

import physio

for session_name in physio.session.get_sessions():
    logging.debug("\tprocessing %s" % session_name)
    try:
        physio.summary.summarize.summarize_session(session_name)
    except Exception as E:
        logging.error("Session %s failed with %s" % \
                (session_name, str(E)))
