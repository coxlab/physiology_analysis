#!/usr/bin/env python

#import collections
import logging

import numpy
import pylab

#Attributes = collections.defaultdict(dict)
default_attributes = {
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
        'rtype': { \
                'getter': lambda c, k, d: get_rtype(c, k, d),
                'default': -1,
                },
        #'maxresp': { \
        #        'getter': lambda c, k, d: get_max_response(c, k, d),
        #        'default': numpy.nan,
        #        },
        }


def get_responses(cell, key, default):
    responses = {}
    for (rtype, d) in cell['resps'].iteritems():
        b = d['b_mean']
        if b == 0:
            b = 1
        m = d['mean']
        r = m / b
        responses[rtype] = r
    return responses


def get_rtype(cell, key, default):
    try:
        resps = get_responses(cell, key, default)
        return max(resps, key=lambda k: resps[k])
    except:
        return default


def get_max_response(cell, key, default):
    try:
        resps = get_responses(cell, key, default)
        return max(resps.values())
    except:
        return default


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


def try_get(dictionary, default_value, key, *others):
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
            return try_get(dictionary[key], default_value, \
                    others[0], *others[1:])
        else:
            #print "d[key]: %s" % key
            return dictionary[key]
    except KeyError as E:
        #logging.debug("KeyError: key: %s[%s]" % (key, E))
        return default_value


def setup_attributes(attrs):
    for k in attrs:
        if 'getter' not in attrs[k].keys():
            attrs[k]['getter'] = lambda c, k, d: try_get(c, d, *k.split('.'))
        if 'default' not in attrs[k].keys():
            attrs[k]['default'] = numpy.nan
        attrs[k]['values'] = []


def make_attribute(key, default=None, getter=None, op=None):
    if isinstance(key, dict):
        # key already an attribute
        assert len(key.keys()) == 1, \
                "cannot make attribute with dictionary with >1 key: %s" \
                % key.keys()
        attrs = key
        key = key.keys()[0]
    else:
        attrs = {}
        attrs[key] = {}
    if default is not None:
        attrs[key]['default'] = default
    if getter is not None:
        attrs[key]['getter'] = getter
    if op is not None:
        attrs[key]['getter'] = lambda c, k, d: \
                op(try_get(c, d, *tuple(k.split('.'))))
    return key, attrs


def parse_cell(cell, attrs):
    for k in attrs:
        attrs[k]['values'].append( \
                attrs[k]['getter'](cell, k, attrs[k]['default']))


def parse_cells(cells, attrs):
    [parse_cell(cell, attrs) for cell in cells]


def extract_data(attrs):
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


def parse_data(cells, attrs=None, include_defaults=True, full=False):
    if attrs is None:
        attrs = default_attributes
    elif include_defaults:
        attrs.update(default_attributes)
    setup_attributes(attrs)
    logging.debug("Extracting attributes: %s" % attrs)
    parse_cells(cells, attrs)
    if full:
        return extract_data(attrs), attrs
    else:
        return extract_data(attrs)
