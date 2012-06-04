#!/usr/bin/env python

import logging
import sys

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab
import pymongo

from physio.plotting.sliding_window import sliding_window_apply

save = False

use_sliding_window = True
fancy_color = False
stat_to_compute = numpy.mean
log_transform_stat = False
one_minus_and_log_transform_stat = False
weak_cull = False
no_scaling = False
thresh = None
vmax = None
vmin = None

plot_im = True
to_plot = 'responsivity'
#to_plot = 'tol_Xp'

min_cells = 1

if to_plot is 'tol_X':
    key = 'tolerance.stats.X'
    log_transform_stat = False
    one_minus_and_log_transform_stat = False
if to_plot is 'tol_Xp':
    key = 'tolerance.stats.Xp'
    log_transform_stat = True
    one_minus_and_log_transform_stat = False
elif to_plot is 'F':
    key = 'selectivity.name.stats.F'
    log_transform_stat = False
    one_minus_and_log_transform_stat = False
elif to_plot is 'Fp':
    key = 'selectivity.name.stats.Fp'
    log_transform_stat = True
    one_minus_and_log_transform_stat = False
    #thresh = -numpy.log(0.1)
    #vmin = None
elif to_plot is 'Xp':
    key = 'selectivity.name.stats.Xp'
    log_transform_stat = True
    one_minus_and_log_transform_stat = False
elif to_plot is 'Hp':
    key = 'selectivity.name.stats.Hp'
    log_transform_stat = True
    one_minus_and_log_transform_stat = False

elif to_plot is 'X':
    key = 'selectivity.name.stats.X'
    log_transform_stat = False
    one_minus_and_log_transform_stat = False
elif to_plot is 'sel':
    key = 'selectivity.name.stats.sel'
    log_transform_stat = False
    one_minus_and_log_transform_stat = False
    #thresh = -numpy.log(0.1)
elif to_plot is 'sep':
    key = 'separability.name.pos_x.stats.spi'
    log_transform_stat = False
    one_minus_and_log_transform_stat = True
elif to_plot is 'samp':
    key = 'ap'
    no_scaling = True
    weak_cull = True
elif to_plot is 'responsivity':
    key = 'responsivity.p'
    log_transform_stat = True
    one_minus_and_log_transform_stat = False
    weak_cull = True
elif to_plot is 'resp':
    key = 'responsivity.p'
    log_transform_stat = True
    one_minus_and_log_transform_stat = False
    weak_cull = False

    def at_least_length_one(x):
        if len(x) > 0:
            return 1.0

    stat_to_compute = at_least_length_one
else:
    key = 'vrate'
    log_transform_stat = False
    one_minus_and_log_transform_stat = False

cmap = pylab.cm.hot


# This can also be called like: by_location.py <key>
if len(sys.argv) > 1:
    key = sys.argv[1]

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
        'selectivity.name.stats.F': { \
                'default': numpy.nan,
                },
        # 'vrate': { \
        #         'getter': lambda c, k, d: try_get(c, numpy.nan, 'driven_mean')\
        #         / try_get(c, numpy.nan, 'baseline_mean'),
        #         }
        }

if key not in attrs.keys():
    attrs[key] = {}

if weak_cull:
    query['nspikes'] = {'$gt': 1000}
else:
    query['nspikes'] = {'$gt': 1000}
    query['responsivity.p'] = {'$lt': 0.1}
#query['animal'] = 'K4'

server = {'host': 'coxlabanalysis1.rowland.org',
        #'host': 'soma2.rowland.org',
        'db': 'physiology',
        #'coll': 'cells_sep'}
        'coll': 'cells_rerun'}


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
        dtype.append((k, type(attrs[k]['values'][0])))
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
data = data[data['dv'] < 0]
data = data[data['ap'] < -3]
print "After to position culling: %i" % len(data)


pylab.figure()
pylab.subplot(131)
tex = [-7, -8.5]
tey1 = [-3.8, -2.2]
tey2 = [-5.6, -4.4]
pylab.fill_between(tex, tey1, tey2, alpha=0.1, color='k')

if no_scaling:
    pylab.scatter(data['ap'], data['dv'],
                  edgecolors='none', alpha=0.3)
else:
    pylab.scatter(data['ap'], data['dv'], s=data[key] * 25,
                  edgecolors='none', alpha=0.3)

#pylab.title("Red = selective(alpha=0.05)")
pylab.xlabel('AP (mm)')
pylab.ylabel('DV (mm)')
xt, _ = pylab.xticks()
pylab.xticks(xt, rotation=90)

sp = pylab.subplot(132)


def filter_min_cells(x):
    if len(x) > min_cells:
        return x
    else:
        return []

filter_nans = lambda x: [x1 for x1 in filter_min_cells(x) if not numpy.isnan(x1)]

if log_transform_stat:
    stat = lambda x: stat_to_compute(-numpy.log(filter_nans(x)))
elif one_minus_and_log_transform_stat:
    stat = lambda x: stat_to_compute(-numpy.log(1.0 - numpy.array(filter_nans(x))))
else:
    stat = lambda x: stat_to_compute(filter_nans(x))


if plot_im:

    if use_sliding_window:

        d, (X, Y) = sliding_window_apply(stat,
                                        zip(data['ap'], data['dv']),
                                        data[key],
                                        window_size=0.5,
                                        n_points=30)
        print d

        if thresh is not None:
            d[d < thresh] = numpy.nan

        im_extents = [X[0, 0], X[0, -1], Y[0, 0], Y[-1, 0]]
        print(im_extents)

        if fancy_color:
            color_im = cmap(d)

            count, _ = sliding_window_apply(numpy.sum,
                                            zip(data['ap'], data['dv']),
                                            data[key],
                                            window_size=0.5,
                                            n_points=50)
            count_norm = numpy.median(count.ravel())
            color_im[:, :, 3] = count / count_norm
            pylab.imshow(color_im, aspect='equal', origin='lower',
                         extent=im_extents)

        else:

            pylab.imshow(numpy.flipud(d), interpolation='nearest',
                         aspect='equal',
                         origin='upper',
                         extent=im_extents,
                         cmap=cmap,
                         vmin=vmin,
                         vmax=vmax)

            pylab.hold(True)

    else:
        d, x, y = numpy.histogram2d(data['ap'], data['dv'], \
                bins=[10, 10], weights=data[key])
        w, _, _ = numpy.histogram2d(data['ap'], data['dv'], \
                bins=[10, 10])
        d *= 1. / w
        pylab.imshow(d.T, interpolation='nearest', \
                     aspect='equal', \
                     origin='lower', \
                     extent=[x[0], x[-1], y[0], y[-1]],
                     cmap=cmap)

    if not fancy_color:
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

if save:
    pylab.savefig('%s_by_location.svg' % key)
else:
    pylab.show()
