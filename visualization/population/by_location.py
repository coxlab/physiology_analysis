#!/usr/bin/env python

import logging

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab
import pymongo

query = {}

query['nspikes'] = {'$gt': 1000}
query['responsivity.p'] = {'$lt': 0.1}
#query['animal'] = 'K4'

server = {'host': 'coxlabanalysis1.rowland.org',
        'db': 'physiology',
        'coll': 'cells_sel'}

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

for cell in cursor:
    rate = cell.get('driven_mean', numpy.nan)
    base = cell.get('baseline_mean', numpy.nan)
    ap, dv, ml = cell.get('location', [numpy.nan] * 3)
    Fp = try_get(cell, numpy.nan, 'selectivity', 'name', 'stats', 'Fp')
    F = try_get(cell, numpy.nan, 'selectivity', 'name', 'stats', 'F')
    sel = try_get(cell, numpy.nan, 'selectivity', 'name', 'stats', 'sel')
    spi = try_get(cell, 0, 'separability', 'name', 'pos_x', 'stats', \
            'spi')
    if base != 0:
        vrate = rate / base
    else:
        vrate = numpy.nan

    data.append((ap, dv, ml, base, rate, vrate, F, Fp, sel, spi))

if len(data) == 0:
    print "No data found"
    raise Exception("No data found")
data = pylab.array(data, dtype=[('ap', float), ('dv', float), ('ml', float), \
        ('base', float), ('rate', float), ('vrate', float), ('F', float), \
        ('Fp', float), \
        ('sel', float), ('spi', float)])

print "Prior to position culling: %i" % len(data)
data = data[data['dv'] < 0]
data = data[data['ap'] < -3]
print "After to position culling: %i" % len(data)


#key = 'sel'
#key = 'vrate'
#key = 'F'
key = 'spi'

pylab.figure()
pylab.subplot(131)
tex = [-7, -8.5]
tey1 = [-3.8, -2.2]
tey2 = [-5.6, -4.4]
pylab.fill_between(tex, tey1, tey2, alpha=0.1, color='k')
pylab.scatter(data['ap'], data['dv'], s=data[key], \
        c=(data['Fp'] < 0.05).astype(int), \
        edgecolors='none', alpha=0.3)
pylab.title("Red = selective(alpha=0.05)")
pylab.xlabel('AP (mm)')
pylab.ylabel('DV (mm)')
xt, _ = pylab.xticks()
pylab.xticks(xt, rotation=90)

pylab.subplot(132)
d, x, y = numpy.histogram2d(data['ap'], data['dv'], \
        bins=[10, 10], weights=data[key])
w, _, _ = numpy.histogram2d(data['ap'], data['dv'], \
        bins=[10, 10])
d *= 1. / w
pylab.imshow(d.T, interpolation='nearest', \
        aspect='equal', \
        origin='lower', \
        extent=[x[0], x[-1], y[0], y[-1]])
pylab.colorbar()
pylab.xlabel('AP')
xt, _ = pylab.xticks()
pylab.xticks(xt, rotation=90)
pylab.ylabel('DV')

pylab.subplot(233)
d, x = numpy.histogram(data['dv'], weights=data[key])
w, _ = numpy.histogram(data['dv'])
d *= 1. / w
cx = (x[1:] - x[:-1]) / 2. + x[:-1]
pylab.plot(cx, d)
pylab.xlabel('DV')
pylab.ylabel(key)

pylab.subplot(236)
d, x = numpy.histogram(data['ap'], weights=data[key])
w, _ = numpy.histogram(data['ap'])
d *= 1. / w
cx = (x[1:] - x[:-1]) / 2. + x[:-1]
pylab.plot(cx, d)
pylab.xlabel('AP')
pylab.ylabel(key)

pylab.show()
