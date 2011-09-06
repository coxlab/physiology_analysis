#!/usr/bin/env python

import logging, sys
logging.basicConfig(level = logging.DEBUG)

import numpy as np
import pylab as pl

import physio

plotWindow = [-0.25, .75]
plotNBins = 20
channel = 7
# nChannels = 32
# depthOrdered = physio.channelmapping.position_to_tdt(range(nChannels))

session = physio.session.load('K4_110720')

trialTimes, stimuli, _, _ = session.get_trials()
nTrials = len(trialTimes)
logging.debug("N Trials: %i" % nTrials)

stimCounts = physio.events.stimuli.count(stimuli)
uniqueStimuli = physio.events.stimuli.unique(stimuli)
for s in stimCounts.keys():
    logging.debug("\t%i presentations of %s" % (stimCounts[s],s))

# get unique positions & sizes
pxs = {}
pys = {}
sizes = {}
names = {}
for s in uniqueStimuli:
    pxs[s['pos_x']] = 1
    pys[s['pos_y']] = 1
    sizes[s['size_x']] = 1
    names[s['name']] = 1
names = sorted(names.keys())
pxs = sorted(pxs.keys())
pys = sorted(pys.keys())
sizes = sorted(sizes.keys())

# generate x & y arrays
# 120 total :-O
#[name, :], [name, px, py[1], :], [name, px[1], py, :], [name, size, :]
conditions = []
for n in names:
    conditions.append({'name' : n})
# conditions = uniqueStimuli
# data = [(ch,cl) for ch in depthOrdered for cl in range(1,6)]
data = [(channel, cl) for cl in range(1,6)]


subplotsWidth = len(conditions)
subplotsHeight = len(data)
pl.figure(figsize=(subplotsWidth*2, subplotsHeight*2))
# pl.gcf().suptitle('%s %d' % (groupBy, group))
pl.subplot(subplotsHeight, subplotsWidth,1)
logging.debug("Plotting %i by %i plots(%i)" % (subplotsWidth, subplotsHeight, subplotsWidth * subplotsHeight))

ymax = 0
for (y, datum) in enumerate(data):
    for (x, condition) in enumerate(conditions):
        logging.debug("\tPlotting[%i, %i]: ch/cl %s : s %s" % (x, y, datum, condition))
        trials, _, _, _ = session.get_trials(condition)
        spikes = session.get_spike_times(*datum)
        pl.subplot(subplotsHeight, subplotsWidth, subplotsWidth * y + x)
        physio.plotting.psth.plot(trials, spikes, plotWindow[0], plotWindow[1], plotNBins)
        pl.axvline(0., color = 'k')
        pl.axvspan(0., 0.5, color = 'k', alpha = 0.1)
        
        if x == 0: pl.ylabel('Cluster: %i' % datum[1])
        if y == 0: pl.title('%s' % str(condition), rotation=45)
        if y < len(data): pl.xticks([])
        ymax = max(ymax, pl.ylim()[1])

session.close()

for y in xrange(subplotsHeight):
    for x in xrange(subplotsWidth):
        pl.subplot(subplotsHeight, subplotsWidth, subplotsWidth * y + x)
        pl.ylim(0,ymax)
        
pl.savefig("psth.png")