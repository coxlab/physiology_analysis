#!/usr/bin/env python

import numpy
import pylab

import scipy.optimize


def gaussian(x, A=1, mu=1, sigma=1):
    return numpy.real(A * numpy.exp(-(x - mu) ** 2. / (2. * sigma ** 2)))


def direct_fit(data, x):
    mu = numpy.sum(x * data) / numpy.sum(data)
    sigma = numpy.sqrt(numpy.abs(numpy.sum((x - mu) ** 2 * data) \
            / numpy.sum(data)))
    A = data.max()
    return A, mu, sigma


def iterative_fit(data, x, *args, **kwargs):
    # guess
    p0 = direct_fit(data, x)

    # fit
    fit = lambda p: data - gaussian(x, *p)
    r, info = scipy.optimize.leastsq(fit, p0, *args, **kwargs)
    return r[0], r[1], r[2]

if __name__ == '__main__':
    noise = 0.1
    A = 3
    mu = 30
    sigma = 3

    # generate data
    x = numpy.arange(100)
    data = gaussian(x, A, mu, sigma)
    data += pylab.randn(data.size) * noise

    # fit
    da, dm, ds = direct_fit(data, x)
    fa, fm, fs = iterative_fit(data, x)

    # print
    print "\tactual\tdirect\tfit"
    print "A:\t%.2f\t%.2f\t%.2f" % (A, da, fa)
    print "mu:\t%.2f\t%.2f\t%.2f" % (mu, dm, fm)
    print "sigma:\t%.2f\t%.2f\t%.2f" % (sigma, ds, fs)

    # plot
    pylab.plot(data, 'g')
    pylab.plot(gaussian(x, da, dm, ds), 'r')
    pylab.plot(gaussian(x, fa, fm, fs), 'b')
    pylab.show()
