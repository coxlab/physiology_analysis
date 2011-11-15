#!/usr/bin/env python

import logging, optparse, os, sys
logging.basicConfig(level = logging.DEBUG)
#import matplotlib
import numpy as np
import pylab as pl

import physio

rwin = (0.1,0.2)
bwin = (-0.1,0)

sessionName = 'K4_110804'
epochNumber = 0
channel = 2
cluster = 4

config = physio.cfg.load(sessionName)
#epochs = []
#if len(args) == 2:
#    epochs = [int(args[1]),]
#else
#    epochs = range(physio.session.get_n_epochs(config))

session = physio.session.load(sessionName, epochNumber)

spikes = session.get_spike_times(channel, cluster)

# get baseline firing rate

trialTimes, stimuli, _, _ = session.get_trials()
targetTimes, blueStimuli = session.get_stimuli(stimType = 'rectangle')
allStimTimes = trialTimes + targetTimes
assert len(trialTimes) + len(targetTimes) == len(allStimTimes)

# get driven firing rate
bspikes = physio.spikes.stats.event_lock(allStimTimes, spikes, bwin[0], bwin[1], unpack=True)
brate = len(bspikes) / (float(bwin[1] - bwin[0]) * len(allStimTimes))
print "Baseline rate: %f spikes per second" % brate

# get all stim ids, stim positions, stim sizes
uniqueStimuli = physio.events.stimuli.unique(stimuli)
ids = {}
sizes = {}
posxs = {}
posys = {}
for s in uniqueStimuli:
    ids[s['name']] = 1
    sizes[s['size_x']] = 1
    posxs[s['pos_x']] = 1
    posys[s['pos_y']] = 1
ids = sorted(ids.keys())
sizes = sorted(sizes.keys())
posxs = sorted(posxs.keys())
posys = sorted(posys.keys())
print ids, sizes, posxs, posys

# sort id by response (plot id)
idRates = {}
for stimId in ids:
    trials, _, _, _ = session.get_trials({'name' : stimId})
    sspikes = physio.spikes.stats.event_lock(trials, spikes, rwin[0], rwin[1], unpack=True)
    idRates[stimId] = len(sspikes) / (float(rwin[1] - rwin[0]) * len(trials))
print "ID Rates:", idRates
idByRate = sorted(idRates, key=idRates.get)
minId = idByRate[0]
maxId = idByRate[-1]
midI = int(len(idByRate)/2)
midId = idByRate[midI]
print "Min, mid, max:", minId, midId, maxId

pl.figure()
pl.suptitle("%s:%i[%i]" % (sessionName, channel, cluster))
pl.subplot(211)
pl.subplot(224)
rates = [idRates[i] for i in idByRate]
names = idByRate
colors = ['k' for i in xrange(len(rates))]
colors[0] = 'b'
colors[midI] = 'g'
colors[-1] = 'r'
pl.vlines(range(len(rates)), pl.zeros(len(rates)), rates, colors=colors, lw=5.0)
pl.xticks(range(len(rates)), names)
pl.ylabel("Firing Rate (Hz)")
pl.axhline(brate)
pl.xlabel("Stimulus Id")
pl.xlim((-1,len(rates)+1))

# collapse across position (plot size)
def get_rate(spikes, condition, rwin):
    trials, _, _, _ = session.get_trials(condition)
    if len(trials) == 0:
        raise ValueError("no trials for condition: %s" % str(condition))
    s = physio.spikes.stats.event_lock(trials, spikes, rwin[0], rwin[1], unpack=True)
    return len(s) / (float(rwin[1] - rwin[0]) * len(trials))

pl.subplot(223)
rateBySize = []
for i,c in zip((minId, midId, maxId),('b','g','r')):
    rates = []
    for size in sizes:
        rates.append(get_rate(spikes, {'name': i, 'size_x': size}, rwin))
    rateBySize.append(rates)
    pl.plot(rates, color=c)
pl.xticks(range(len(sizes)), [str(s) for s in sizes])
pl.xlabel("Stimulus Size (degrees)")
pl.ylabel("Firing Rate (Hz)")
pl.axhline(brate)
pl.xlim((-1,len(sizes)+1))
print "Rate By Size", rateBySize

# collapse across size (plot position)
poss = []
for y in posys:
    row = []
    for x in posxs:
        row.append(x)
    poss.append(row)

rateByPos = pl.ones((3, len(posys), len(posxs))) * brate
for (ii, i) in enumerate((minId, midId, maxId)):
    for (iy, y) in enumerate(posys):
        for (ix, x) in enumerate(posxs):
            try:
                rate = get_rate(spikes, {'name': i, 'pos_x': x, 'pos_y':y}, rwin)
                rateByPos[ii,iy,ix] = rate
                #rates.append(get_rate(spikes, {'name': i, 'pos_x': x, 'pos_y':y}, rwin))
            except ValueError as E:
                print E
print rateByPos
cmaps = (pl.cm.Blues, pl.cm.Greens, pl.cm.Reds)
for (i,cm) in enumerate(cmaps):
    pl.subplot(231+i)
    rates = rateByPos[i]
    pl.xticks(range(len(posxs)), ["%.1f" % x for x in posxs])
    pl.yticks(range(len(posys)), ["%.1f" % y for y in posys])
    pl.imshow(rates, interpolation='nearest', cmap=cm)
    for y in xrange(rates.shape[0]):
        for x in xrange(rates.shape[1]):
            pl.text(x,y,"%.1f" % rates[y,x], ha='center', va='center')
    #pl.xticks(range(len(posxs)), ["%.1f" % x for x in posxs])
    #pl.yticks(range(len(posys)), ["%.1f" % y for y in posys])
    if i == 0:
        pl.xlabel("X Position (degrees)")
        pl.ylabel("Y Position (degrees)")

# save plot
pl.savefig("test.png")
