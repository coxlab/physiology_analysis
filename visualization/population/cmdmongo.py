#!/usr/bin/env python

import ast
import copy
import logging
import optparse

import pymongo

default_query = {
    'nspikes': {'$gt': 1000},
    'responsivity.p': {'$lt': 0.1},
    'driven_mean': {'$gt': 2},
    'snr_mean': {'$gt': 1},
    }


def parse_query_string(string):
    """
    this is ugly for now so something like:
        {'nspikes': {'$gt': 10}}
    requires:
        "{'nspikes': {'\$gt': 10}}"
    """
    return ast.literal_eval(string)


def add_to_query(option, opt, value, parser):
    if not hasattr(parser.values, option.dest):
        parser.values = option.default
    getattr(parser.values, option.dest).update(parse_query_string(value))
    logging.debug("New query: %s" % getattr(parser.values, option.dest))


def setup_parser(parser=None, query=None):
    if parser is None:
        parser = optparse.OptionParser()
    if query is None:
        query = {}  # defaults are set in 'parse'
    parser.add_option('-q', '--query', help='mongo query',
            default=query, action='callback', callback=add_to_query,
            nargs=1, type='string')
    parser.add_option('-H', '--host', help='mongo host',
            default='coxlabanalysis1.rowland.org')
    parser.add_option('-d', '--db', help='mongo db',
            default='physiology')
    parser.add_option('-c', '--coll', help='mongo collection',
            default='cells_merge')
    return parser


def parse(parser=None, query=None, include_defaults=True):
    if query is None:
        query = default_query
    elif include_defaults:
        query.update(default_query)
    parser = setup_parser(parser, query)
    return parser.parse_args()


def connect(options):
    return pymongo.Connection(options.host)[options.db][options.coll]


if __name__ == '__main__':
    p = setup_parser()
    o, a = p.parse_args()
    for k in 'query host db coll'.split():
        print '%s = %s' % (k, getattr(o, k))
