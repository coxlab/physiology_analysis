#!/usr/bin/env python

import logging

rtype_attributes = {
        'rtype': { \
                'getter': lambda c, k, d: get_rtype(c, k, d),
                'default': 'Fail',
                },
        }


def get_responses(cell, key, default):
    responses = {}
    for (rtype, d) in cell['resps'].iteritems():
        b = d['b_mean']
        bs = d['b_std']
        m = d['mean']
        if bs == 0:
            bs = 1
        r = (m - b) / bs
        #r = m / b
        responses[rtype] = r
    return responses


def get_rtype(cell, key, default):
    try:
        resps = get_responses(cell, key, default)
        #t = ""
        #for k, v in resps.iteritems():
        #    if abs(v) > 1:
        #        t += '%s/' % str(k)
        #if len(t):
        #    t = t[:-1]
        #return str(t)
        return str(max(resps, key=lambda k: resps[k]))
    except Exception as E:
        logging.debug("get_rtype failed: %s" % E)
        return default


def get_max_response(cell, key, default):
    try:
        resps = get_responses(cell, key, default)
        return max(resps.values())
    except:
        return default
