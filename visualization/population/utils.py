#!/usr/bin/env python

import logging

import attribute
import cmdmongo


def fetch(attrs=None, parser=None, query=None, full=False):
    opts, args = cmdmongo.parse(parser, query)
    cells = cmdmongo.connect(opts)
    logging.debug("Issuing query: %s" % opts.query)
    logging.debug("N Cells prior to query: %s" % cells.count())
    cursor = cells.find(opts.query)
    logging.debug("N Cells post query: %s" % cursor.count())
    if full:
        return attribute.parse_data(cursor, attrs), cells, opts, args
    else:
        return attribute.parse_data(cursor, attrs)
