#!/usr/bin/env python

import logging
import optparse

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab

#violin = True
violin = False
try:
    from violinplot import violinplot
except ImportError:
    violin = False

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


key = 'rtype'
rtypes = ['on', 'off', 'sus', 'late']
query = {}
attrs = {}

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

print "Prior to culling: %i" % len(data)

areas = area_divisions.keys()
figs, axes = pylab.subplots(1, len(areas))
for (spi, area) in enumerate(areas):
    print "Area: %s" % area
    datum = data[data['area'] == area][key]
    counts = {}
    urtypes = numpy.unique(datum)
    #for rt in rtypes:
    for rt in urtypes:
        counts[rt] = numpy.sum(datum == rt)
        print "\t%s: %s" % (rt, counts[rt])
    labels = sorted(counts.keys())
    x = [counts[l] for l in labels]
    axes[spi].pie(x, labels=labels)
    axes[spi].set_title(area)

if opts.save:
    #pylab.savefig('%s_by_area.svg' % key)
    pylab.savefig('%s_by_area.png' % key)
else:
    pylab.show()
