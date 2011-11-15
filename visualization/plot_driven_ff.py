#!/usr/bin/env python

import logging, optparse, os, sys
logging.basicConfig(level = logging.DEBUG)
import matploblib
import numpy as np
import pylab as plt

import physio

rwin = (100,200)
bwin = (-100,0)

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
brate = len(bspikes) / float(bwin[1] - bwin[0])
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
    idRates[stimId] = len(sspikes) / float(rwin[1] - rwin[0])
print "ID Rates:", idRates
idByRate = sorted(idRates, key=idRates.get)
minId = idByRate[0]
maxId = idByRate[-1]
midId = idByRate[int(len(idByRate)/2)]
print "Min, mid, max:", minId, midId, maxId

# collapse across position (plot size)

# collapse across size (plot position)

# save plot
