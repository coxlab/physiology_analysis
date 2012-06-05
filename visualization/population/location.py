#!/usr/bin/env python

import logging

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab

import utils

key = 'selectivity.name.stats.F'
#key = 'friedman.stats.Q'
#key = 'friedman.stats.p'
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

data, cells, opts, args = utils.fetch(attrs=attrs, query=query, full=True,
        default_key=key)

key_label = opts.operation.replace('x', opts.key)

if len(data) == 0:
    print "No data found"
    raise Exception("No data found")

print "Prior to position culling: %i" % len(data)
data = data[data['dv'] < 0]
data = data[data['ap'] < -3]
print "After to position culling: %i" % len(data)

data = data[numpy.logical_not(numpy.isnan(data[opts.key]))]
print "After nan culling: %i" % len(data)


pylab.figure()
pylab.subplot(131)
tex = [-7, -8.5]
tey1 = [-3.8, -2.2]
tey2 = [-5.6, -4.4]
pylab.fill_between(tex, tey1, tey2, alpha=0.1, color='k')
pylab.scatter(data['ap'], data['dv'], s=data[opts.key] * 25, \
#        c=(data['Fp'] < 0.05).astype(int), \
        edgecolors='none', alpha=0.3)
#pylab.title("Red = selective(alpha=0.05)")
pylab.xlabel('AP (mm)')
pylab.ylabel('DV (mm)')
xt, _ = pylab.xticks()
pylab.xticks(xt, rotation=90)

pylab.subplot(132)
d, x, y = numpy.histogram2d(data['ap'], data['dv'], \
        bins=[10, 10], weights=data[opts.key])
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
d, x = numpy.histogram(data['dv'], weights=data[opts.key])
w, _ = numpy.histogram(data['dv'])
d *= 1. / w
cx = (x[1:] - x[:-1]) / 2. + x[:-1]
pylab.plot(cx, d)
pylab.xlabel('DV')
pylab.ylabel(key_label)

pylab.subplot(236)
d, x = numpy.histogram(data['ap'], weights=data[opts.key])
w, _ = numpy.histogram(data['ap'])
d *= 1. / w
cx = (x[1:] - x[:-1]) / 2. + x[:-1]
pylab.plot(cx, d)
pylab.xlabel('AP')
pylab.ylabel(key_label)

if opts.save:
    #pylab.savefig(opts.filename)
    #pylab.savefig('%s_by_location.svg' % key)
    pylab.savefig('%s_by_location.png' % key_label)
else:
    pylab.show()
