#!/usr/bin/env python

import logging
import sys

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab
import pymongo
import scipy.stats

import attribute
import utils


#key = 'selectivity.name.stats.F'
key = 'friedman.stats.Q'
#key = 'selectivity.name.stats.Fp'
#key = 'selectivity.name.stats.sel'
#key = 'selectivity.pos_x.stats.sel'
#key = 'selectivity.pos_y.stats.sel'
#key = 'selectivity.size_x.stats.sel'
#key = 'vrate'


op = None

query = {}
attrs = {}

if (len(sys.argv) > 1) and (sys.argv[1][0] != '-'):
        key = sys.argv[1]
key, kattrs = attribute.make_attribute(key, op=op)
attrs.update(kattrs)

data, cells, opts, args = utils.fetch(attrs=attrs, query=query, full=True)

if len(data) == 0:
    print "No data found"
    raise Exception("No data found")

print "Prior to position culling: %i" % len(data)
#data = data[data['dv'] < 0]
#data = data[data['ap'] < -3]
print "After to position culling: %i" % len(data)

data = data[numpy.logical_not(numpy.isnan(data[key]))]
print "After nan culling: %i" % len(data)

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

if opts.save:
    #pylab.savefig('%s_by_area.svg' % key)
    pylab.savefig('%s_by_area.png' % key)
else:
    pylab.show()
