#!/usr/bin/env python

import pickle

import numpy
import pylab

import fit_gaussian


def get_cells():
    return pickle.load(open('cells.p'))

# keys: grand, sel, max
cells = get_cells()

Nm = 4

data = []

for cell in cells:
    sel = cell['sel']

    # grand
    gys = numpy.array(cell['grand']['means'])
    if len(gys) < Nm:
        continue
    gxs = numpy.array(cell['grand']['sorted'])
    gA, gmu, gsigma = fit_gaussian.iterative_fit(gys, gxs)
    gmax = gys.max()
    if gA > gmax * 2:
        continue

    # max
    mys = numpy.array(cell['max']['means'])
    if len(mys) < Nm:
        continue
    mxs = numpy.array(cell['max']['sorted'])
    mA, mmu, msigma = fit_gaussian.iterative_fit(mys, mxs)
    mmax = mys.max()
    if mA > mmax * 2:
        continue

    data.append((sel, gA, gmu, gsigma, gmax, mA, mmu, msigma, mmax))
    continue

    pylab.subplot(211)
    pylab.scatter(gxs, gys, c='g')
    sx = numpy.array(sorted(gxs))
    sx = numpy.linspace(sx[0], sx[-1], 100)
    pylab.plot(sx, fit_gaussian.gaussian(sx, gA, gmu, gsigma), c='r')
    ga = "A: %.2f, mu: %.2f, sig: %.2f" % (gA, gmu, gsigma)
    pylab.title('Grand: %.2f : %s' % (sel, ga))
    #xl = pylab.xlim()
    #cx = xl[0]  # (xl[1] - xl[0]) / 2. + xl[0]
    #yl = pylab.ylim()
    #cy = (yl[1] - yl[0]) / 2. + yl[0]
    #ga = "A: %.2f, mu: %.2f, sig: %.2f" % (gA, gmu, gsigma)
    #pylab.text(cx, cy, "A: %.2f, mu: %.2f, sig: %.2f" % (gA, gmu, gsigma))

    pylab.subplot(212)
    pylab.scatter(mxs, mys, c='g')
    sx = numpy.array(sorted(mxs))
    sx = numpy.linspace(sx[0], sx[-1], 100)
    pylab.plot(sx, fit_gaussian.gaussian(sx, mA, mmu, msigma), c='r')
    ga = "A: %.2f, mu: %.2f, sig: %.2f" % (mA, mmu, msigma)
    pylab.title('Max %s: %.2f : %s' % (cell['max']['name'], sel, ga))

    #xl = pylab.xlim()
    #cx = xl[0]  # (xl[1] - xl[0]) / 2. + xl[0]
    #yl = pylab.ylim()
    #cy = (yl[1] - yl[0]) / 2. + yl[0]
    #pylab.text(cx, cy, "A: %.2f, mu: %.2f, sig: %.2f" % (mA, mmu, msigma))

    pylab.show()

data = pylab.array(data, dtype=[('sel', float), ('gA', float), ('gmu', float),\
        ('gsigma', float), ('gmax', float), ('mA', float), ('mmu', float), \
        ('msigma', float), ('mmax', float)])

# cull
print "Before culling: len(data) = %i" % len(data)
data = data[data['gsigma'] < 360]
data = data[data['msigma'] < 360]
data = data[data['gmu'] < 180]
data = data[data['gmu'] > -180]
data = data[data['mmu'] < 180]
data = data[data['mmu'] > -180]
print "After culling: len(data) = %i" % len(data)

pylab.subplot(221)
pylab.scatter(data['sel'], data['gsigma'])
pylab.xlabel('sel')
pylab.ylabel('gsigma')

pylab.subplot(222)
pylab.scatter(data['sel'], data['msigma'])
pylab.xlabel('sel')
pylab.ylabel('msigma')

pylab.subplot(223)
pylab.hist(data['gsigma'], bins=50)
pylab.xlabel('gsigma')

pylab.subplot(224)
pylab.hist(data['msigma'], bins=50)
pylab.xlabel('msigma')

pylab.show()
