#!/usr/bin/env python

import logging
import optparse

import numpy  # useful for opts.operation

import attribute
import cmdmongo
import plotting


def setup_parser(parser=None):
    if parser is None:
        parser = optparse.OptionParser()
    parser.add_option('-o', '--operation', type='string', default='x')
    return parser


def fetch(attrs=None, parser=None, query=None, full=False, default_key=None):
    if attrs is None:
        attrs = {}
    parser = plotting.setup_parser(setup_parser(parser))  # do this first
    opts, args = cmdmongo.parse(parser, query)
    op = lambda x: eval(opts.operation)
    cells = cmdmongo.connect(opts)
    logging.debug("Issuing query: %s" % opts.query)
    logging.debug("N Cells prior to query: %s" % cells.count())
    cursor = cells.find(opts.query)
    logging.debug("N Cells post query: %s" % cursor.count())
    if len(args):  # assume this is a key
        key = args[0]
    else:
        key = default_key
    if key is not None:  # command line key overrides kwarg key
        key, kattrs = attribute.make_attribute(key, op=op)
        attrs.update(kattrs)
    opts.key = key
    if full:
        return attribute.parse_data(cursor, attrs), cells, opts, args
    else:
        return attribute.parse_data(cursor, attrs)
