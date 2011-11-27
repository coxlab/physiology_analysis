#!/usr/bin/env python

import sys

import pylab as pl

from mayavi import mlab

filename = '../reports/summaryfile_111125'

badSessions = ['fake0_110908','L2_111014','L2_110930','L2_110927','L2_111004','L2_110922','L1_111118']
minspikes = 100
minrate = 0.001
minsnr = 1.#3.0
minepoch = 60#45 * 60 # only >45 min sessions

if len(sys.argv) > 1:
    filename = sys.argv[1]

colnames = ['session','enum','estart','eend','ch','cl','ml','ap','dv','snr','snrstd','nspikes','rate', 'brate', 'drate']
coltypes = ['S16','i4','i4','i4','i4','i4','f4','f4','f4','f8','f8','i4','f8', 'f8', 'f8']

d = pl.loadtxt(filename, dtype={'names': colnames, 'formats' : coltypes})

print "Raw:", d.shape

# remove bad animals
for bs in badSessions:
    d = d[d['session'] != bs]
print "After removing bad sessions:", d.shape

# remove short sessions
d = d[(d['eend'] - d['estart']) >= minepoch]
print "After removing short (<%i second) epoch:" % minepoch, d.shape

# remove min spikes
d = d[d['nspikes'] >= minspikes]
print "After removing low (<%i) spike counts:" % minspikes, d.shape

# remove slow cells
d = d[d['rate'] >= minrate]
print "After removing slow (<%f) rates:" % minrate, d.shape

# remove low snr spikes
d = d[d['snr'] >= minsnr]
print "After removing low (<%.3f) snr spikes:" % minsnr, d.shape

# remove highly variable spikes: stderr > mean
d = d[ (d['snr'] / (d['snrstd'] / pl.sqrt(d['nspikes']))) > 1.]
#d = d[((d['snrstd'] / pl.sqrt(d['nspikes'])) / d['snr']) > 2.]
print "After removing highly variable spikes:", d.shape

print
nsessions = len(pl.unique(d['session']))
print "Number of sessions   :", nsessions
ncells = len(d)
print "Number of cells      :", ncells
print "Avg cells per session:", ncells / float(nsessions)

# ----------------- plotting ----------

if False:
    pl.figure()
    pl.subplot(221)
    pl.hist(d['snr'], bins=100)
    pl.xlabel('SNR')

    pl.subplot(222)
    pl.hist((d['snrstd']/pl.sqrt(d['nspikes'])), bins=100)
    pl.xlabel('std(SNR)/sqrt(NSpikes)')

    pl.subplot(223)
    pl.hist(d['nspikes'], bins=100)
    pl.xlabel('NSpikes')

    pl.subplot(224)
    pl.hist(d['rate'], bins=100)
    pl.xlabel('Rate')

pdata = d[(d['dv'] < 0.) & (d['ml'] > 0)]

## snr
#w = pl.log(pdata['snr'])
#title = "log(snr)"
#fn = "log_snr"

# driven rate 
#xs = pdata['ml']
#ys = pdata['ap']
#zs = pdata['dv']
xs = pdata['dv']
ys = pdata['ml']
zs = pdata['ap']
ws = pdata['drate'] - pdata['brate']
title = "driven rate"
fn = "driven_rate"

figure = mlab.figure(fgcolor=(1,1,1), size=(800,600))
figure.scene.disable_render = True
#mlab.points3d(pdata['ml'],pdata['ap'],pdata['dv'],pl.log(pdata['snr']))
#glyphs = mlab.points3d(pdata['ml'],pdata['ap'],pdata['dv'],w)
glyphs = mlab.points3d(xs,ys,zs,ws)
mlab.scalarbar(orientation='vertical',title=title)
#mlab.axes(xlabel='ML',ylabel='AP',zlabel='DV',color=(1,1,1))
mlab.axes(xlabel='DV',ylabel='ML',zlabel='AP',color=(1,1,1))
#mlab.view(azimuth=270,reset_roll=True)

loffset = 0.05
pid = ws.argmax()
session = pdata['session'][pid]
ch = pdata['ch'][pid]
cl = pdata['cl'][pid]
w = ws[pid]
t = "%s:%i[%i]=%f" % (session, ch, cl, w)
label = mlab.text3d(xs[pid]+loffset,ys[pid]+loffset,zs[pid]+loffset,t,scale=0.1)

def label_point(pid):
    session = pdata['session'][pid]
    ch = pdata['ch'][pid]
    cl = pdata['cl'][pid]
    w = ws[pid]
    label.text = "%s:%i[%i]=%f" % (session, ch, cl, w)
    label.position = [xs[pid]+loffset, ys[pid]+loffset, zs[pid]+loffset]
#outline = mlab.outline()#line_width=3)
#outline.outline_mode = 'cornered'
#pid = 100
#od = 0.00001
#outline.bounds = (xs[pid]-od, xs[pid]+od,
#                ys[pid]-od, ys[pid]+od,
#                zs[pid]-od, zs[pid]+od)
figure.scene.disable_render = False

glyph_pts = glyphs.glyph.glyph_source.glyph_source.output.points.to_array()
def picker_callback(picker):
    if picker.actor in glyphs.actor.actors:
        #print picker.actor
        pid = picker.point_id/glyph_pts.shape[0]
        if pid != -1:
            label_point(pid)
            #print pid
            #session = pdata['session'][pid]
            #ch = pdata['ch'][pid]
            #cl = pdata['cl'][pid]
            #print session, ch, cl
#            outline.bounds = (xs[pid]-od, xs[pid]+od,
#                            ys[pid]-od, ys[pid]+od,
#                            zs[pid]-od, zs[pid]+od)

picker = figure.on_mouse_pick(picker_callback)
picker.tolerance = 0.01

mlab.savefig("%s.png" % fn)
mlab.savefig("%s.obj" % fn)
mlab.show()
