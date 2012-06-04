# -*- coding: utf-8 -*-
from matplotlib.pyplot import figure, show
from scipy.stats import gaussian_kde
from numpy.random import normal
from numpy import arange, array, newaxis


def violinplot(ax, data, pos, bp=False):
    '''
    create violin plots on an axis
    '''
    if not len(data):
        return
    data = array(data)
    if data.ndim == 1:
        data = data[newaxis, :]
    if (not hasattr(pos, '__getitem__')):
        pos = [pos]
        dist = 1
    else:
        dist = max(pos) - min(pos)
    w = min(0.15 * max(dist, 1.0), 0.5)
    for datum, p in zip(data, pos):
        k = gaussian_kde(datum)  # calculates the kernel density
        m = k.dataset.min()  # lower bound of violin
        M = k.dataset.max()  # upper bound of violin
        x = arange(m, M, (M - m) / 100.)  # support for violin
        v = k.evaluate(x)  # violin profile (density curve)
        v = v / v.max() * w  # scaling the violin to the available space
        ax.fill_betweenx(x, p, v + p, facecolor='y', alpha=0.3)
        ax.fill_betweenx(x, p, -v + p, facecolor='y', alpha=0.3)
    if bp:
        ax.boxplot(data, notch=1, positions=pos, vert=1)

if __name__ == "__main__":
    pos = range(5)
    data = [normal(size=100) for i in pos]
    fig = figure()
    ax = fig.add_subplot(111)
    violinplot(ax, data, pos, bp=1)
    show()
