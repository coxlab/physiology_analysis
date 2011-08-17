#!/usr/bin/env python

import ast, copy, logging, optparse, os, pickle, sys
logging.basicConfig(level=logging.DEBUG)

import tables
import matplotlib
import numpy as np
import pylab as plt

# add path of physio module
import sys
sys.path.append('../')
import physio

parser = optparse.OptionParser(usage="usage: %prog [options] resultsfile")
parser.add_option("-c", "--cluster", dest="cluster", default=19)
if sys.platform == 'darwin':
    parser.add_option("-f", "--file", dest="file", default="../results/K4_110720/K4_110720_597_to_5873.h5")
else:
    parser.add_option("-f", "--file", dest="file", default="/data/results/K4_110720/K4_110720_597_to_5873.h5")
(options, args) = parser.parse_args()
options.cluster = int(options.cluster)

timebase, stimtimer, spiketimes, epoch_mw = physio.load.load_cluster(options.file, options.cluster)

# things I need
# 1. baseline firing rate
baseline = physio.caton_utils.get_n_spikes(stimtimer.get_all_times(), spiketimes, -0.1, 0, timebase)
baseline = baseline / float(len(stimtimer.get_all_times())) / 0.1
print "Baseline firing rate: %.2f" % baseline

visualResponses = {} # ordered like times in stimtimer
stimReps = {}
for st in stimtimer.times:
    visualResponses[st] = physio.caton_utils.get_n_spikes(stimtimer.times[st], spiketimes, 0.1, 0.2, timebase)
    stimReps[st] = len(stimtimer.times[st])
visualResponses = np.array(sorted(visualResponses.iteritems(), key=lambda x: x[0]))[:,1]
stimReps = np.array(sorted(stimReps.iteritems(), key=lambda x: x[0]))[:,1]

stimnamelist = stimtimer.get_unique_stim_attr('intName')
stimnames = np.array(stimtimer.get_stim_attr('intName'))

def collate_responses(stimname, attr):
    stimIs = np.where(stimnames == stimname)[0]
    uniquelist = stimtimer.get_unique_stim_attr(attr)
    values = np.array(stimtimer.get_stim_attr(attr))
    resp = []
    for us in uniquelist:
        valIs = np.where(values == us)[0]
        Is = np.union1d(valIs, stimIs)
        resp.append([us, sum(visualResponses[Is]), sum(stimReps[Is])])
    return resp

stimresps = {}
nameresps = []
for sn in stimnamelist:
    # stim_name, n_spikes, n_reps
    nameresps.append([sn, sum(visualResponses[stimnames == sn]), sum(stimReps[stimnames == sn])])
    # stim_name attr : attr_name, n_spikes, n_reps
    stimresps[sn] = {}
    stimresps[sn]['x'] = collate_responses(sn,'pos_x')
    stimresps[sn]['y'] = collate_responses(sn,'pos_y')
    stimresps[sn]['s'] = collate_responses(sn,'size_x')

print "Response by ID:", nameresps
f = open('clusters/resp_%i.p' % options.cluster,'wb')
pickle.dump((baseline, nameresps, stimresps), f)
f.close()

# 2. NORMALIZED response to each stimulus collapsed across variation (and corresponding driven firing rate)
#   stimID ...
#   [raster] [raster] ....
#   [psth]  [psth] ...

# 2. normalized histograms for a single id given variation: pos_x/pos_y, size
# pos:
#    stimID ...
# size1  [-y]
#    [-x]  [+x]
#       [+y]
# size2...
