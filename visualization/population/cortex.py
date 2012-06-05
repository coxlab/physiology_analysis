#!/usr/bin/env python

import logging
import optparse
import sys

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab
#import pymongo

import brainatlas

import utils

key = 'selectivity.name.stats.F'
#key = 'friedman.stats.Q'
#key = 'friedman.stats.p'
#op = lambda v: -numpy.log(v)
op = None
#key = {
#        'one': {
#            'default': 1,
#            },
#        }
#key = {
#        'friedman.stats.Q': {
#            'getter': lambda c, k, d: \
#                    -numpy.log(
#                    attribute.try_get(c, [d] * 2, \
#                        *tuple('friedman.stats.p'.split('.')))[1]),
#            'default': numpy.nan,
#            },
#        }

query = {}  # try to use the commandline
attrs = {}

parser = optparse.OptionParser()
parser.add_option('-x', '--cylinderx', type='float', default=2)
parser.add_option('-y', '--cylindery', type='float', default=6)
parser.add_option('-a', '--areas', default='TeA V2L V1B')
parser.add_option('-S', '--sizescale', type='float', default=25.)

data, cells, opts, args = utils.fetch(parser=parser, attrs=attrs, \
        query=query, full=True, default_key=key)

key_label = opts.operation.replace('x', opts.key)

if len(data) == 0:
    print "No data found"
    raise Exception("No data found")

print "Prior to culling: %i" % len(data)
#data = data[data['dv'] < 0]
#data = data[data['ap'] < -3]
#print "After to position culling: %i" % len(data)

data = data[numpy.logical_not(numpy.isnan(data[opts.key]))]
print "After nan culling: %i" % len(data)
print "After culling: %i" % len(data)

# project locations onto cylindrical coordinates
cts, crs = ([], [])
for datum in data:
    ml = datum['ml']
    dv = -datum['dv']  # flip dv
    ct, cr = brainatlas.cylinder.project(ml, dv, \
            opts.cylinderx, opts.cylindery)
    cts.append(ct)
    crs.append(cr)

data = pylab.rec_append_fields(data, ['ct', 'cr'], [cts, crs])

apts = brainatlas.construct.load_points('areas.p')
for area in opts.areas.split():
    pts = numpy.array(apts[area])
    pts = pts[pts[:, 0] > 0]
    brainatlas.cylinder.plot_area_points(pts, \
            opts.cylinderx, opts.cylindery, \
            label=area, alpha=0.1)
pylab.scatter(data['ap'], data['ct'], label=key_label, \
        s=data[key] * opts.sizescale)
pylab.legend()
if opts.save:
    pylab.savefig("%s_by_cortex.png" % key)
else:
    pylab.show()
