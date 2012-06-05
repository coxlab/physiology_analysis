#!/usr/bin/env python

import logging
import optparse

logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab
import scipy.stats
from matplotlib.patches import Rectangle

import utils
import utils.cmdmongo

textcolor = 'w'
bgcolor = 'k'
screencolor = 'w'
iconcolor = 'k'

parser = optparse.OptionParser()
parser.add_option('-s', '--session', default='M4_120202')
parser.add_option('-S', '--save', default=False, action='store_true')
parser.add_option('-i', '--cid', default='27.1')
opts, args = utils.cmdmongo.parse(parser, query={}, include_defaults=False)

opts.query['animal'], opts.query['date'] = opts.session.split('_')
opts.query['ch'], opts.query['cl'] = \
        [int(i) for i in opts.cid.strip().split('.')]

conn = utils.cmdmongo.connect(opts)
cells = [c for c in conn.find(opts.query)]

if len(cells) != 1:
    for c in cells:
        print c['animal'], c['session'], c['ch'], c['cl']
    raise Exception("Query did not match only 1 cell: %i" % len(cells))

cell = cells[0]


def load_images(indices):
    images = []
    for i in indices:
        im = pylab.imread('thumbs/Stim_%i_bg.png' % int(i))
        images.append(im)
    return images

r = numpy.array(cell['friedman']['rmean'])
b = numpy.array(cell['friedman']['bmean'])
trans = numpy.array(cell['friedman']['trans'])
ids = numpy.array(cell['friedman']['ids'])
id_imgs = numpy.array(load_images(ids))

d = r - b
# r = [id, trans]
shape = d.shape

idi = numpy.mean(d, 1).argsort()
ti = numpy.mean(d, 0).argsort()

f = pylab.figure(facecolor=bgcolor)
#pylab.subplot(111, axisbg='k')
pylab.imshow(d[idi][:, ti], interpolation='nearest')
pylab.yticks(numpy.arange(len(ids)), ids[idi])
#pylab.yticks(numpy.arange(len(ids)), [])
yl = pylab.ylim()
xl = pylab.xlim()

# plot ids
for (i, im) in enumerate(id_imgs[idi]):
    h, w = im.shape[:2]
    s = 1 / float(w) if w > h else 1 / float(h)
    cx = -1.
    cy = i
    hw = w * s / 2.
    hh = h * s / 2.
    extent = (cx - hw, cx + hw, cy - hh, cy + hh)
    pylab.imshow(im, origin=(-1, i), extent=extent)

# plot transformations
ax = pylab.gca()
for (i, t) in enumerate(trans[ti]):
    cx = i
    cy = -1.
    sw, sh = 114.75274765881358, 64.54842055808264
    sd = max(sw, sh)
    hsw = sw / 2.
    hsh = sh / 2.
    px, py, r, sx, sy = t
    py = -py  # flip y
    w = sx / sd
    h = sy / sd
    x = (px + hsw) / sd
    y = (py + hsh) / sd
    # first border (x,y) = lower left
    ax.add_artist(Rectangle((cx - sw / sd / 2., cy - sh / sd / 2.), \
            sw / sd, sh / sd, fill=True, ec='0.5', fc=screencolor))
    # add a box, size w,h, at x y
    #ax.add_artist(Rectangle((cx - .5 + x - w / 2., cy - 1. + y + h/2.), \
    #        w, h, fill=True, ec='k'))
    ll = (cx - sw / sd / 2. + x - w / 2., cy - sh / sd / 2. + y - h / 2.)
    ax.add_artist(Rectangle(ll, w, h, fill=True, ec=iconcolor, fc=iconcolor))

pylab.ylim([yl[0], -1.5])
pylab.xlim([-1.5, xl[1]])
ax.set_axis_off()
pylab.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)

title = '%s_%s:%s [%s]' % (cell['animal'], cell['date'], \
        cell['cid'], cell['area'])
pylab.suptitle(title)
if opts.save:
    fn = '%s.png' % title
    pylab.savefig(fn)
else:
    pylab.show()
