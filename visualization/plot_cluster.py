#!/usr/bin/env python

import ast, copy, logging, optparse, os, sys
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

timebase, stimtimer, spiketimes, epoch_mw = physio.load.load_cluster(options.file, options.cluster)

# things I need
# 1. baseline firing rate
baseline = physio.caton_utils.get_n_spikes(stimtimer.get_all_times(), spiketimes, -0.1, 0, timebase)
baseline = baseline / len(stimtimer.get_all_times()) / 0.1
print "Baseline firing rate: %.2f" % baseline

visualResponses = {} # ordered like times in stimtimer
for st in stimtimer.times:
    visualResponses[st] = physio.caton_utils.get_n_spikes(stimtimer.times[st], spiketimes, 0.1, 0.2, timebase)
visualResponses = np.array(sorted(visualResponses.iteritems(), key=lambda x: x[0]))
stimnames = np.array(stimtimer.get_stim_attr('intName'))
stimposx = np.array(stimtimer.get_stim_attr('pos_x'))
stimposy = np.array(stimtimer.get_stim_attr('pos_y'))
stimsize = np.array(stimtimer.get_stim_attr('size_x'))

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
