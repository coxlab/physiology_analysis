#!/usr/bin/env python

import numpy
import scipy.stats

# friedman input is measure_1, measure_2... measure_n
# passing in data organized as [id, trans] like so
# friedman(*data)
# will treat id levels as different measures
# a p < alpha will support that the mean rank order of the
# id response was preserved across transformations
#
# passing in data organized as [trans, id] like so
# friedman(*data)
# will treat trans levls as different measures
# a p < alpha will support that the mean rank order of the
# transformation was preserved across ids

import scipy.stats._support as _support
from scipy.stats import rankdata, find_repeats, chisqprob


def friedmanchisquare(*args):
    """ from scipy.stats """
    k = len(args)
    if k < 3:
        raise ValueError('\nLess than 3 levels.  "\
                "Friedman test not appropriate.\n')
    n = len(args[0])
    for i in range(1, k):
        if len(args[i]) != n:
            raise ValueError('Unequal N in friedmanchisquare.  Aborting.')

    # Rank data
    data = apply(_support.abut, args)
    data = data.astype(float)
    for i in range(len(data)):
        data[i] = rankdata(data[i])

    # Handle ties
    ties = 0
    for i in range(len(data)):
        replist, repnum = find_repeats(numpy.array(data[i]))
        for t in repnum:
            ties += t * (t * t - 1)
    c = 1 - ties / float(k * (k * k - 1) * n)

    ssbn = sum(sum(data) ** 2)
    chisq = (12.0 / (k * n * (k + 1)) * ssbn - 3 * n * (k + 1)) / c
    return chisq, chisqprob(chisq, k - 1), data, ssbn, c


def fake_data(nm=12, ne=7, s=1, n=0.1):
    """
    nm = number of measures (aka number of ids)
    ne = number of elements (aka number of transformations)
    Returns data for a completely transformation invariant cell
    in the shape of [id, transformation]
    """
    return numpy.mgrid[:nm, :ne][0].astype('f8') * \
            s / float(nm - 1) + \
            numpy.random.randn(nm, ne) * n


# without some noise the transposed firedman test fails with:
# stats.py:3577: RuntimeWarning: invalid value encountered in double_scalars
#  chisq = ( 12.0 / (k*n*(k+1)) * ssbn - 3*n*(k+1) ) / c
cdata = fake_data(s=10, n=0.001)

#run = lambda d: scipy.stats.friedmanchisquare(*d)
run = lambda d: friedmanchisquare(*d)
cr = run(cdata)

show = lambda a: numpy.array_str(a, precision=1, suppress_small=True)
print "===== [id, trans] ====="
print "input data:", cdata.shape, "[id, trans]\n", show(cdata)
print "calculated rank:\n", cr[2]
print "Measure 1 (response to ids[0] at trans[:])\n", show(cdata[0])
print "friedman results:", cr[:2], cr[3:]

print "===== Transposed ====="
print "===== [trans, id] ====="
tdata = cdata.T
tr = run(tdata)
print "input data:", tdata.shape, "[trans, id]\n", show(tdata)
print "calculated rank:\n", tr[2]
print "Measure 1 (response at trans[0] to ids[:])\n", show(tdata[0])
print "friedman results:", tr[:2], tr[3:]

#ndata = fake_data(s=.1, n=1)
#nr = run(ndata)
#print "Noisy:"
#print nr
#print show(ndata)
