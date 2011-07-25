#!/usr/bin/env python

import ast, copy, logging, optparse, os, sys
logging.basicConfig(level=logging.DEBUG)

import tables
import matplotlib
# if sys.platform == 'darwin':
#     matplotlib.use('qt4Agg') # doesn't like QT?
import numpy as np
import pylab as plt

# add path of physio module
import sys
sys.path.append('../')
import physio

parser = optparse.OptionParser(usage="usage: %prog [options] resultsfile")
parser.add_option("-x", "--stimgroup", dest="stimgroup", default="name",
                    help="Group stimuli by this variable: name, pos_x, pos_y, size_x...")
parser.add_option("-y", "--spikegroup", dest="spikegroup", default="clusters",
                    help="Group spikes by this variable: clusters or channels")
parser.add_option("-n", "--nbins", dest="nbins", default=14,
                    help="Number of bins in psth")
parser.add_option("-b", "--before", dest="before", default=0.1,
                    help="Seconds before stimulus onset to plot")
parser.add_option("-a", "--after", dest="after", default=0.6,
                    help="Seconds after stimulus onset to plot")
parser.add_option("-g", "--group", dest="group", default=-1,
                    help="Plot only a single group of spikes at index group")

(options, args) = parser.parse_args()

if len(args) != 1:
    parser.print_usage()
    sys.exit(1)

h5filename = args[0]

outDir = os.path.splitext(h5filename)[0] + '/grouped'

resultsFile, tb, stimtimer, spiketimes, clusters, triggers, epoch_mw = physio.load.load(h5filename, clean=True, addToBlacklist=[])
stimgroups = stimtimer.get_unique_stim_attr(options.stimgroup)

if options.spikegroup == 'clusters':
    groupedSpikes = physio.caton_utils.spikes_by_cluster(spiketimes, clusters)
elif options.spikegroup == 'channels':
    groupedSpikes = physio.caton_utils.spikes_by_channel(spiketimes, triggers)

subplots_height = len(groupedSpikes)
subplots_width = len(stimgroups)
logging.debug("subplots w:%i, h:%i" % (subplots_width, subplots_height))

plotWindow = [0.25, .75]
plotNBins = 20

if not os.path.exists(outDir): os.makedirs(outDir)

if options.group != -1:
    spikegroupI = [int(options.group),]
else:
    spikegroupI = range(len(groupedSpikes))
logging.debug("Plotting group indexes: %s" % str(spikegroupI))

plt.figure(figsize=(subplots_width, subplots_height))
plt.gcf().suptitle('%s by %s' % (options.spikegroup, options.stimgroup))
plt.subplot(subplots_height, subplots_width,1)

for (spy, spikegroup) in enumerate(spikegroupI):
    for (spx, stimgroup) in enumerate(stimgroups):
        logging.info("Plotting %s by %s" % (spikegroup, stimgroup))
        stimtimes = []
        for (i,s) in enumerate(stimtimer.stimList):
            if s.__getattribute__(options.stimgroup) == stimgroup:
                stimtimes += stimtimer.times[i]
        n_stim = len(stimtimes)
        logging.info("\tN Stim: %d" % n_stim)
        
        ev_locked = physio.mw_utils.event_lock_spikes(stimtimes, groupedSpikes[spikegroup],
                            options.before, options.after, tb)
        
        spi = spx + spy * subplots_width + 1
        plt.subplot(subplots_height, subplots_width, spi)
        
        # physio.mw_utils.plot_rasters(ev_locked, time_range=(-options.before, options.after), n_bins=options.nbins)
        physio.mw_utils.plot_psth(ev_locked, time_range=(-options.before, options.after), n_bins=options.nbins)
        pre = 0
        post = 0
        for ev in ev_locked:
            for s in ev:
                if s <= 0:
                    pre += 1
                elif s <= 0.5:
                    post += 1
        if pre == 0:
            visual = float(post) / 5.
        else:
            visual = float(post) / (5. * float(pre))
        plt.axvline(0.5, zorder=-500, color='r')
        spb = (options.before + options.after) / options.nbins# seconds per bin
        sps = pre / options.before # spikes per second
        plt.axhline(sps * spb, color='g')
        a = plt.gca()
        a.set_yticks([])
        a.set_yticklabels([])
        xm = a.get_xlim()[0] + (a.get_xlim()[1] - a.get_xlim()[0]) / 2.
        ym = a.get_ylim()[0] + (a.get_ylim()[1] - a.get_ylim()[0]) / 2.
        a.text(xm,ym,'%.2f' % visual, color='k',
            horizontalalignment='center', verticalalignment='center')
        # a.set_yticks([a.get_ylim()[1]])
        # a.set_yticklabels([str(a.get_ylim()[1])],
        #     horizontalalignment='left', color='r', alpha=0.8)
        if spx == 0:
            a.set_ylabel(str(spy), rotation='horizontal',
                horizontalalignment='right', verticalalignment='center')
        if spy != (len(spikegroupI) - 1):
            a.set_xticks([])
            a.set_xticklabels([])
        else:
            a.set_xticks([0.,options.after])
            a.set_xticklabels(['0','%.1f' % options.after])
        if spy == 0:
            a.set_title("%s[%i]" % (stimgroup, n_stim),
                rotation=45, horizontalalignment='left', verticalalignment='bottom')

# plt.show()
plt.savefig("%s/%s_by_%s_psth.svg" % (outDir, options.spikegroup, options.stimgroup))
plt.hold(False)
plt.clf()

resultsFile.close()
