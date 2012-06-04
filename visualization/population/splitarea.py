#!/usr/bin/env python

import logging
import optparse
import sys

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab
import scipy.stats

#violin = True
violin = False
try:
    from violinplot import violinplot
except ImportError:
    violin = False

import attribute
import utils

daxis = 'ap'
#daxis = 'dv'
ndiv = 3

area_divisions = {
        'TeA': {
            'ap': [-4.56, -8.76],
            'dv': [-2.32, -6.7],
            'ml': [7.97, 4.58],
            },
        'V2L': {
            'ap': [-4.56, -9.36],
            'dv': [-1.05, -4.41],
            'ml': [7.28, 3.76],
            },
        'V1B': {
            'ap': [-5.88, -9.36],
            'dv': [-0.63, -3.28],
            'ml': [5.63, 2.57],
            },
        }
#ap
#AuD -3.0 -6.84
#AuV -3.24 -6.84
#PRh -3.0 -9.36
#Au1 -3.24 -6.84
#Ect -3.0 -9.36
#V1M -5.88 -9.36
#dv
#AuD 6.16 2.07
#AuV 6.33 3.9
#PRh 8.13 3.3
##Au1 5.7 2.62
#Ect 7.19 2.46
#V1M 3.0 0.36
#ml
#AuD 7.63 5.3
#AuV 7.97 5.76
#PRh 7.75 4.31
#Au1 7.97 5.65
#Ect 7.89 4.03
#V1M 4.32 1.35


#key = 'selectivity.name.stats.F'
key = 'friedman.stats.Q'
#key = 'selectivity.name.stats.Fp'
#key = 'selectivity.name.stats.sel'
#key = 'selectivity.pos_x.stats.sel'
#key = 'selectivity.pos_y.stats.sel'
#key = 'selectivity.size_x.stats.sel'
#key = 'vrate'


#op = lambda x: -numpy.log(x)
op = None

query = {}
attrs = {}

if (len(sys.argv) > 1) and (sys.argv[1][0] != '-'):
        key = sys.argv[1]
key, kattrs = attribute.make_attribute(key, op=op)
attrs.update(kattrs)

parser = optparse.OptionParser()
parser.add_option('-n', '--ndiv', type='int', default=ndiv)
parser.add_option('-a', '--axis', default=daxis)

data, cells, opts, args = utils.fetch(parser=parser, attrs=attrs, \
        query=query, full=True)
ndiv = opts.ndiv
daxis = opts.axis

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
areas = area_divisions.keys()

subdivs = {}
for area in areas:
    amax, amin = area_divisions[area][daxis]
    edges = numpy.linspace(amin, amax, ndiv + 1, True)
    s = edges[0]
    subdivs[area] = []
    for e in edges[1:]:
        subdivs[area].append([s, e])  # (s, e]
        s = e

uareas = numpy.unique(data['area'])
for ua in uareas:
    if ua not in areas:
        logging.error("Cell in area %s, no divisions defined" % ua)

nareas = len(areas)
figs, axes = pylab.subplots(1, nareas, sharey=True)
for (spi, area) in enumerate(areas):
    ai = data['area'] == area
    #pylab.subplot(1, nareas, spi + 1)
    pylab.sca(axes[spi])
    for (si, sd) in enumerate(subdivs[area]):
        subi = ((data[daxis] >= sd[0]) & (data[daxis] < sd[1]))
        inds = ((ai & subi) & (numpy.logical_not(numpy.isnan(signal))))
        d = signal[inds]
        n = len(d)
        if n == 0:
            continue
        m = numpy.mean(d)
        s = numpy.std(d)
        if violin:
            violinplot(axes[spi], d, si, False)
            pylab.boxplot([d], positions=[si], vert=1)
        else:
            pylab.scatter(si * numpy.ones(len(d)), d, alpha=0.5)
            pylab.errorbar(si, [m], [s / numpy.sqrt(n)], color='r', \
                capsize=10)
    pylab.xticks(range(ndiv), ['%.1f to %.1f' % tuple(sd) \
            for sd in subdivs[area]], rotation=45)
    pylab.xlim(-.5, ndiv - .5)
    pylab.xlabel('%s divisions' % daxis.upper())
    pylab.title('%s' % area)
pylab.sca(axes[0])
pylab.ylabel('%s' % key)
pylab.suptitle(opts.coll)
pylab.subplots_adjust(bottom=.24)
#pylab.gcf().tight_layout()

if opts.save:
    #pylab.savefig('%s_by_area.svg' % key)
    pylab.savefig('%s_by_area.png' % key)
else:
    pylab.show()
