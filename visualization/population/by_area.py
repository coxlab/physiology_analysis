#!/usr/bin/env python

import logging
#import sys

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab
import pymongo
import scipy.stats

save = True
#key = 'selectivity.name.stats.F'
key = 'friedman.stats.Q'
#key = 'selectivity.name.stats.Fp'
#key = 'selectivity.name.stats.sel'
#key = 'selectivity.pos_x.stats.sel'
#key = 'selectivity.pos_y.stats.sel'
#key = 'selectivity.size_x.stats.sel'
#key = 'vrate'

# This can also be called like: by_location.py <key>
#if len(sys.argv) > 1:
#    key = sys.argv[1]

query = {}

attrs = { \
        'ap': { \
                'getter': lambda c, k, d: try_get(c, [d] * 3, 'location')[0],
                'default': numpy.nan,
                },
        'dv': { \
                'getter': lambda c, k, d: try_get(c, [d] * 3, 'location')[1],
                'default': numpy.nan,
                },
        'ml': { \
                'getter': lambda c, k, d: try_get(c, [d] * 3, 'location')[2],
                'default': numpy.nan,
                },
        'area': { \
                'getter': lambda c, k, d: str(try_get(c, d, k)),
                'default': 'Na',
                },
        'selectivity.name.stats.F': { \
                'default': numpy.nan,
                },
        'selectivity.name.stats.Fp': {
                'getter': lambda c, k, d: -numpy.log(try_get(c, d, \
                        *k.split('.'))),
                'default': 1.0,
                },
        'selectivity.name.stats.sel': {
                'default': numpy.nan,
                },
        'selectivity.pos_x.stats.sel': {
                'default': numpy.nan,
                },
        'selectivity.pos_y.stats.sel': {
                'default': numpy.nan,
                },
        'selectivity.size_x.stats.sel': {
                'default': numpy.nan,
                },
        #'vrate': { \
        #        'getter': lambda c, k, d: try_get(c, numpy.nan, 'driven_mean')\
        #        / try_get(c, numpy.nan, 'baseline_mean'),
        #        }
        }

if key not in attrs.keys():
    attrs[key] = {}

query['nspikes'] = {'$gt': 1000}
query['responsivity.p'] = {'$lt': 0.1}
query['driven_mean'] = {'$gt': 2}
query['snr_mean'] = {'$gt': 1}
#query['animal'] = 'K4'

server = {'host': 'coxlabanalysis1.rowland.org',
        'db': 'physiology',
        'coll': 'cells_merge'}

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
        print "KeyError: key: %s" % key
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


def setup_attrs(attrs):
    for k in attrs:
        if 'getter' not in attrs[k].keys():
            attrs[k]['getter'] = lambda c, k, d: try_get(c, d, *k.split('.'))
        if 'default' not in attrs[k].keys():
            attrs[k]['default'] = numpy.nan
        attrs[k]['values'] = []

setup_attrs(attrs)

types = []

for cell in cursor:
    for k in attrs:
        attrs[k]['values'].append( \
                attrs[k]['getter'](cell, k, attrs[k]['default']))


def parse_data(attrs):
    keys = attrs.keys()
    dtype = []
    N = -1
    for k in keys:
        if len(attrs[k]['values']) == 0:
            raise Exception("No data for %s" % k)
        if (N != -1) and (len(attrs[k]['values']) != N):
            raise ValueError("Unequal lengths: %i, %i" % \
                    (len(attrs[k]['values']), N))
        N = len(attrs[k]['values'])
        t = type(attrs[k]['values'][0])
        if t == str:
            t = 'S16'
        dtype.append((k, t))
    data = pylab.recarray(N, dtype=dtype)

    for k in keys:
        for (i, v) in enumerate(attrs[k]['values']):
            data[k][i] = v

    return data

data = parse_data(attrs)

if len(data) == 0:
    print "No data found"
    raise Exception("No data found")

print "Prior to position culling: %i" % len(data)
#data = data[data['dv'] < 0]
#data = data[data['ap'] < -3]
print "After to position culling: %i" % len(data)

signal = data[key]
areas = data['area']
uareas = list(numpy.unique(areas))
if 'Na' in uareas:
    i = uareas.index('Na')
    uareas.pop(i)
    uareas.insert(0, 'Na')
if 'Fail' in uareas:
    i = uareas.index('Fail')
    uareas.pop(i)
    uareas.insert(0, 'Fail')

ddata = {}
means = []
stds = []
ns = []
for ua in uareas:
    d = data[data['area'] == ua][key]
    d = d[numpy.logical_not(numpy.isnan(d))]
    ddata[ua] = d
    means.append(numpy.mean(d))
    stds.append(numpy.std(d))
    ns.append(len(d))

# anova
d = [ddata[k] for k in uareas if k not in ['Fail', 'Na']]
Test, p = scipy.stats.f_oneway(*d)
Test, p = scipy.stats.kruskal(*d)
print "Test: T: %s, p: %s" % (Test, p)

pylab.figure()
x = range(len(uareas))
for (xi, ua) in zip(x, uareas):
    d = ddata[ua]
    n = len(d)
    sx = numpy.ones(n) * xi
    pylab.scatter(sx, d, alpha=0.5)
pylab.errorbar(x, means, stds / numpy.sqrt(ns), color='r', capsize=10)
labels = ["%s[%i]" % (a, n) for (a, n) in zip(uareas, ns)]
pylab.xticks(x, labels)
pylab.xlim(-1, len(uareas))
pylab.ylabel(key)
pylab.xlabel('Area')

pylab.suptitle("Test: %s, p: %s" % (Test, p))

if save:
    #pylab.savefig('%s_by_area.svg' % key)
    pylab.savefig('%s_by_area.png' % key)
else:
    pylab.show()
