#!/usr/bin/env python

import logging
import pickle

logging.basicConfig(level=logging.DEBUG)

import numpy
import pymongo

# attr : selectivity.attr.means/sorted # for all
#      : selectivity.name.sorted[0] # for max name
#      : selectivity.name.attr.means/sorted # for max name

sel_key = 'selectivity.name.stats.F'
attr = 'pos_x'

query = {}
query['nspikes'] = {'$gt': 1000}
query['responsivity.p'] = {'$lt': 0.1}
#query['animal'] = 'K4'

server = {'host': 'coxlabanalysis1.rowland.org',
        'db': 'physiology',
        'coll': 'cells_sep'}

cells = pymongo.Connection(server['host'])[server['db']][server['coll']]

logging.info("Raw N Cells: %i" % cells.count())
logging.debug("Query: %s" % str(query))

cursor = cells.find(query)

logging.info("Query N Cells: %i" % cursor.count())


def try_get(d, dval, key, *others):
    """
    Try to get a value from a nested dictionary

    Example
    ----
    d = {'a': 1, 'b': {'1': 'I', '2': {'A': 1}}}
    try_get(d, 'none', 'b', '2', 'A')
    # returns: 1
    try_get(d, 'none', 'b', '2', 'C')
    # returns: 'none'
    """
    try:
        if len(others) != 0:
            #print "tget: %s %s %s %s" % (key, dval, others[0], others[1:])
            return try_get(d[key], dval, others[0], *others[1:])
        else:
            #print "d[key]: %s" % key
            return d[key]
    except KeyError:
        #print "dval: %s" % dval
        return dval


def test_try_get():
    d = {'a': 1, 'b': {'1': 'I', '2': {'A': 1}}}

    def ap(f, v):
        r = f
        t = (r == v)
        print "R: %s [%s]" % (r, t)
        assert(t)
    ap(try_get(d, 'none', 'a'), 1)
    ap(try_get(d, 'none', 'c'), 'none')
    ap(try_get(d, 'none', 'b', '1'), 'I')
    ap(try_get(d, 'none', 'b', '3'), 'none')
    ap(try_get(d, 'none', 'b', '2', 'A'), 1)
    ap(try_get(d, 'none', 'b', '2', 'B'), 'none')

data = []

# attr : selectivity.attr.means/sorted # for all
#      : selectivity.name.sorted[0] # for max name
#      : selectivity.name.attr.means/sorted # for max name

for cell in cursor:
    # get selectivity for name
    sel = try_get(cell, numpy.nan, *sel_key.split('.'))
    if numpy.isnan(sel):
        print "sel is nan"
        continue

    # get overall responses for attr
    grand = {}
    N = 0
    for sub_key in ['means', 'sorted', 'ns']:
        s = 'selectivity.%s.%s' % (attr, sub_key)
        grand[sub_key] = try_get(cell, [], *s.split('.'))
        N = len(grand[sub_key])
    if N < 2:
        print "<2 %s" % attr
        continue

    # get responses for attr at max name
    at_max = {}
    at_max['name'] = try_get(cell, [''], \
            *'selectivity.name.sorted'.split('.'))[0]
    for sub_key in ['means', 'sorted', 'ns']:
        s = 'selectivity.name.%s.%s' % (attr, sub_key)
        at_max[sub_key] = try_get(cell, [], *s.split('.'))
        N = len(at_max[sub_key])
    if N < 2:
        print "<2 %s at max" % attr
        continue

    data.append({'grand': grand, 'max': at_max, 'sel': sel})

if len(data) == 0:
    raise Exception("No data found")

print "Dumping %i cells" % len(data)
pickle.dump(data, open('cells.p', 'w'))
