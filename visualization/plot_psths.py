#!/usr/bin/env python

import ast, copy, logging, os, sys
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

resultsFile = '../results/session_597_to_5873_a32_batch.h5'
if len(sys.argv) > 1:
    resultsFile = sys.argv[1]

#outDir = './psths'
if len(sys.argv) > 4:
    outDir = sys.argv[4]
else:
    outDir = os.path.splitext(resultsFile)[0] + '/psths'
    #logging.debug("Writing plots to: %s" % outDir)

groupBy = 'channels'
if len(sys.argv) > 2:
    groupBy = sys.argv[2]

outDir += '/' + groupBy + '/'
logging.debug("Writing plots to: %s" % outDir)

groupI = None
if len(sys.argv) > 3:
    try:
        groupI = ast.literal_eval(sys.argv[3])
    except:
        pass

if not (groupBy in ['clusters', 'channels']):
    raise ValueError("GroupBy[arg3] must be either clusters or channels NOT %s" % groupBy)

plotWindow = [0.25, .75]
plotNBins = 20

logging.debug("Opening results file: %s" % str(resultsFile))
resultsFile = tables.openFile(resultsFile)

# load time base
timebase = physio.pixel_clock.TimeBase(*physio.h5_utils.get_time_matches(resultsFile))

# load epoch
epoch_mw = physio.h5_utils.get_mw_epoch(resultsFile)
start_mw, end_mw = epoch_mw
logging.debug("Loaded epoch: %s" % str(epoch_mw))

# get stimulus times
logging.debug("Get stimulus times")
stimtimer = physio.h5_utils.get_stimtimer(resultsFile)
stim_names = stimtimer.get_unique_stim_attr('name')
pos_xs = stimtimer.get_unique_stim_attr('pos_x')
pos_ys = stimtimer.get_unique_stim_attr('pos_y')
size_xs = stimtimer.get_unique_stim_attr('size_x')

print stim_names
print pos_xs
print pos_ys
print size_xs

for (l,s) in zip([stim_names,pos_xs,pos_ys,size_xs],['names','pos_x','pos_y','size_x']):
    logging.debug("Found %i %s" % (len(l),s))

subplots_height = len(stim_names)

valid_stims = []
for s in size_xs:
    for y in pos_ys:
        for x in pos_xs:
            for name in stim_names:
                stim = physio.stimsorter.Stim({'name':name,
                            'pos_x': x, 'pos_y': y,
                            'size_x': s, 'size_y': s,
                            'rotation': 0})
                if stimtimer.find_stim(stim) != -1:
                    stim.name = '' # set name to blank for name free matching later
                    valid_stims.append(stim)
                    break

subplots_width = len(valid_stims)
logging.debug("subplots w:%i, h:%i" % (subplots_width, subplots_height))

# fix timebase audio offset
timebase.audio_offset = -timebase.mw_time_to_audio(start_mw)

times = [ x["time"] for x in resultsFile.root.SpikeTable.iterrows()]
clusters = [ x["clu"] for x in resultsFile.root.SpikeTable.iterrows()]
triggers = [ x["st"] for x in resultsFile.root.SpikeTable.iterrows()]

probeDict = physio.h5_utils.get_probe_gdata(resultsFile)
bad_nn_channels = ast.literal_eval('['+probeDict['badsites']+']')
times, clusters, triggers = physio.stats.clean_spikes(times, clusters, triggers, bad_nn_channels)

if groupBy == 'clusters':
    groupedSpikes = physio.caton_utils.spikes_by_cluster(times, clusters)
elif groupBy == 'channels':
    groupedSpikes = physio.caton_utils.spikes_by_channel(times, triggers)

if not os.path.exists(outDir): os.makedirs(outDir)

if groupI is None:
    groupI = xrange(len(groupedSpikes))
else:
    try:
        groupI = iter(groupI)
    except TypeError:
        groupI = [groupI,]

for group in groupI:
    logging.info("Plotting %s %d" % (groupBy, group))
    
    plt.figure(figsize=(subplots_width, subplots_height))
    plt.gcf().suptitle('%s %d' % (groupBy, group))
    plt.subplot(subplots_height, subplots_width,1)
    
    for (subplots_y, sn) in enumerate(stim_names):
        for (subplots_x, vs) in enumerate(valid_stims):
            stim = copy.deepcopy(vs)
            stim.name = sn
            stim.intName = int(sn)
            
            stimI = stimtimer.find_stim(stim)
            if stimI == -1:
                #logging.debug("%s" % stimtimer.stimList)
                #raise ValueError("stimulus: %s was not found when plotting" % stim)
                logging.debug("Stim not found: %s" % str(stim))
                continue
            
            stim_times = [s for s in stimtimer.times[stimI]]
            # stim_times = [s for s in stimtimer.times[stimI] if s < end_mw and s > start_mw]
            n_stim = len(stim_times)
            # n_stim = len([s for s in stim_times if s <= end_mw and s > start_mw])
            
            ev_locked = physio.mw_utils.event_lock_spikes( stim_times,
                                                groupedSpikes[group], plotWindow[0], plotWindow[1],
                                                timebase )
            subplots_i = subplots_x + subplots_y * subplots_width + 1
            plt.subplot(subplots_height, subplots_width, subplots_i)
            physio.mw_utils.plot_rasters(ev_locked, time_range=(-plotWindow[0], plotWindow[1]), n_bins=plotNBins)
            plt.axvline(0.5, zorder=-500, color='r')
            a = plt.gca()
            a.set_yticks([])
            a.set_yticklabels([])
            xm = a.get_xlim()[0] + (a.get_xlim()[1] - a.get_xlim()[0]) / 2.
            ym = a.get_ylim()[0] + (a.get_ylim()[1] - a.get_ylim()[0]) / 2.
            a.text(xm,ym,'%i' % n_stim, color='r', zorder=-1000,
                horizontalalignment='center', verticalalignment='center')
            # a.set_yticks([a.get_ylim()[1]])
            # a.set_yticklabels([str(a.get_ylim()[1])],
            #     horizontalalignment='left', color='r', alpha=0.8)
            if subplots_x == 0:
                a.set_ylabel(stim.name, rotation='horizontal',
                    horizontalalignment='right', verticalalignment='center')
            if subplots_y != (len(stim_names) - 1):
                a.set_xticks([])
                a.set_xticklabels([])
            else:
                a.set_xticks([0.,plotWindow[1]])
                a.set_xticklabels(['0','%.1f' % plotWindow[1]])
            if subplots_y == 0:
                a.set_title('%i,%i[%i]' % (stim.pos_x, stim.pos_y, stim.size_x),
                    rotation=45, horizontalalignment='left', verticalalignment='bottom')
    # plt.show()
    plt.savefig("%s/%s_%d_psth.svg" % (outDir, groupBy, group))
    plt.hold(False)
    plt.clf()

resultsFile.close()
