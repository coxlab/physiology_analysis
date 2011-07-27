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
parser.add_option("-s", "--spikegroup", dest="spikegroup", default="clusters",
                    help="Group spikes by this variable: clusters or channels")
parser.add_option("-b", "--before", dest="before", default=0.1,
                    help="Seconds before stimulus onset to calculate baseline")
parser.add_option("-a", "--after", dest="after", default=0.5,
                    help="Seconds after stimulus onset to calculate response")
parser.add_option("-g", "--group", dest="group", default="",
                    help="Plot group or groups. parsed with ast.literal_eval")

(options, args) = parser.parse_args()

if len(args) != 1:
    parser.print_usage()
    sys.exit(1)

h5filename = args[0]

outDir = os.path.splitext(h5filename)[0] + '/driven'

resultsFile, tb, stimtimer, spiketimes, clusters, triggers, epoch_mw = physio.load.load(h5filename, clean=False) # blacklists bluesquare
channels = physio.stats.single_channel_triggers_to_channels(triggers)

if options.spikegroup == 'clusters':
    groupedSpikes = physio.caton_utils.spikes_by_cluster(spiketimes, clusters)
elif options.spikegroup == 'channels':
    groupedSpikes = physio.caton_utils.spikes_by_channel(spiketimes, channels)

if options.group != "":
    ps = ast.literal_eval(options.group)
    try:
        spikegroupI = iter(ps)
        spikegroupI = ps
        logging.debug("Spike group argument is iterable: %s" % str(spikegroupI))
    except:
        spikegroupI = [int(ps),]
        logging.debug("Spike group argument was an int: %s" % str(spikegroupI))
else:
    spikegroupI = range(len(groupedSpikes))
logging.debug("Plotting group indexes: %s" % str(spikegroupI))

if not os.path.exists(outDir): os.makedirs(outDir)



# get stimulus times
allstimtimes = []
for sk in stimtimer.times:
    allstimtimes += stimtimer.times[sk]

def get_times_by_attr(stimtimer, attr):
    times = {}
    for (i,s) in enumerate(stimtimer.stimList):
        aval = s.__getattribute__(attr)
        times[aval] = times.get(aval, []) + stimtimer.times[i]
    return times

def get_times_by_attr3(stimtimer, attr1, attr2, attr3):
    times = {}
    for (i, s) in enumerate(stimtimer.stimList):
        a1 = s.__getattribute__(attr1)
        a2 = s.__getattribute__(attr2)
        a3 = s.__getattribute__(attr3)
        if (a1 in times):
            if (a2 in times[a1]):
                times[a1][a2][a3] = times[a1][a2].get(a3, []) + stimtimer.times[i]
            else:
                times[a1][a2] = {a3: stimtimer.times[i]}
        else: # a1 not in times
            times[a1] = {a2: {a3: stimtimer.times[i]}}
    return times

idtimes = get_times_by_attr(stimtimer, 'name')
sxytimes = get_times_by_attr3(stimtimer, 'name', 'pos_x', 'pos_y')
logging.debug("stim times by x y: %s" % str(sxytimes))
sxstimes = get_times_by_attr3(stimtimer, 'name', 'pos_x', 'size_x')
logging.debug("stim times by x s: %s" % str(sxstimes))
systimes = get_times_by_attr3(stimtimer, 'name', 'pos_y', 'size_x')
logging.debug("stim times by y s: %s" % str(systimes))

def get_rate(times, spikes, before, after, tb):
    locked_spikes = physio.mw_utils.event_lock_spikes(times, spikes, before, after, tb)
    if len(locked_spikes) == 0:
        del locked_spikes
        logging.warning("Found no spikes for range: %f %f" % (before, after))
        return 0
    
    rate = 0
    for s in locked_spikes:
        rate += len(s)
    
    rate = (rate / float(len(locked_spikes))) * (1. / float(before + after))
    del locked_spikes
    return rate

def plot_rate(stimtimer, times, xattr, lattr, spikes, before, after, timebase, baseline):
    # times = #get_times_by_attr3(stimtimer, stimid, lattr, xattr)
    rates = {}
    for l in times:
        rates[l] = {}
        for x in times[l]:
            rates[l][x] = get_rate(times[l][x], spikes, before, after, timebase) - baseline
    
    plt.hold(True)
    logging.debug("Plotting %s by %s" % (xattr, lattr))
    logging.debug("Rates: %s" % rates)
    for l in sorted(rates.keys(), key=lambda x: int(x)):
        data = sorted(rates[l].iteritems(), key=lambda x: int(x[0]))
        x = [int(d[0]) for d in data]
        y = [d[1] for d in data]
        logging.debug("Plotting line: %s %s" % (lattr, l))
        logging.debug("x: %s" % str(x))
        logging.debug("y: %s" % str(y))
        plt.plot(x,y,label=str(l),marker='o')
    plt.xticks(x)
    # plt.ylim((-2,4))
    # plt.legend()

for spikegroup in spikegroupI:
    logging.info("Plotting %s %i" % (options.spikegroup[:-1], spikegroup))
    
    # for each cluster/channel
    # get baseline
    baseline = get_rate(allstimtimes, groupedSpikes[spikegroup], options.before, 0, tb)
    logging.info("Baseline for %i : %f" % (spikegroup, baseline))
    
    subplots_height = len(idtimes)
    subplots_width = 3 # x,y x,s y,s
    logging.debug("subplots w:%i, h:%i" % (subplots_width, subplots_height))
    plt.figure(figsize=(subplots_width*2, subplots_height*2))
    plt.subplots_adjust(wspace=0.5, hspace=0.5)
    plt.gcf().suptitle('Driven ff by %s [base:%.2f]' % (options.spikegroup, baseline))
    plt.subplot(subplots_height, subplots_width,1)
    
    # calculate driven firing rate for each stimulus id
    rate_by_id = {}
    for stimid in idtimes:
        rate_by_id[stimid] = get_rate(idtimes[stimid], groupedSpikes[spikegroup], 0, options.after, tb) - baseline
        # locked_spikes = physio.mw_utils.event_lock_spikes(idtimes[stimid], groupedSpikes[spikegroup],
        #                     0, options.after, tb)
        # rate = 0
        # for s in locked_spikes:
        #     rate += len(s)
        # 
        # rate_by_id[stimid] = (rate / float(len(locked_spikes))) * (1. / float(options.after)) # in spikes per second
    
    # sort stimulus ids by driven firing rate
    id_by_rate = sorted(rate_by_id.iteritems(), key=lambda x: x[1])
    logging.debug("Stim ID sorted by Rate: %s" % str(id_by_rate))
    
    # for each stimulus id
    ymin, ymax = 0, 0
    for spy in xrange(len(id_by_rate)):
        (stimid, rate) = id_by_rate[spy]
        # # get rates
        # rate_by_pos_x = {}
        # for pos_x in posxtimes[stimid]:
        #     rate_by_pos_x[pos_x] = get_rate(posxtimes[stimid][pos_x], groupedSpikes[spikegroup], 0, options.after, tb) - baseline
        # rate_by_pos_x = sorted(rate_by_pos_x.iteritems(), key=lambda x: int(x[0]))
        # logging.debug("Rate by pos_x for stim %s : %s" % (stimid, rate_by_pos_x))
        # 
        # rate_by_pos_y = {}
        # for pos_y in posytimes[stimid]:
        #     rate_by_pos_y[pos_y] = get_rate(posytimes[stimid][pos_y], groupedSpikes[spikegroup], 0, options.after, tb) - baseline
        # rate_by_pos_y = sorted(rate_by_pos_y.iteritems(), key=lambda x: int(x[0]))
        # logging.debug("Rate by pos_y for stim %s : %s" % (stimid, rate_by_pos_y))
        # 
        # rate_by_size_x = {}
        # for size_x in sizextimes[stimid]:
        #     rate_by_size_x[size_x] = get_rate(sizextimes[stimid][size_x], groupedSpikes[spikegroup], 0, options.after, tb) - baseline
        # rate_by_size_x = sorted(rate_by_size_x.iteritems(), key=lambda x: int(x[0]))
        # logging.debug("Rate by size_x for stim %s : %s" % (stimid, rate_by_size_x))
        
        # plot driven firing rate by pos_x by pos_y : subplot 1
        plt.subplot(subplots_height, subplots_width, spy * subplots_width + 1)
        logging.debug("Subplot: %i" % (spy * subplots_width + 1))
        plot_rate(stimtimer, sxytimes[stimid], 'pos_x', 'pos_y', groupedSpikes[spikegroup], 0, options.after, tb, baseline)
        plt.ylabel('%s[%.2f]' % (stimid, rate))
        if spikegroup == spikegroupI[-1]: plt.xlabel('Pos X')
        if spy == 0: plt.title('B:-5 G:0 R:+5')
        yl = plt.ylim()
        ymin = min(yl[0],ymin)
        ymax = max(yl[1],ymax)
        
        # plot driven firing rate by pos_x by size_x : subplot 2
        plt.subplot(subplots_height, subplots_width, spy * subplots_width + 2)
        logging.debug("Subplot: %i" % (spy * subplots_width + 2))
        plot_rate(stimtimer, sxstimes[stimid], 'pos_x', 'size_x', groupedSpikes[spikegroup], 0, options.after, tb, baseline)
        if spikegroup == spikegroupI[-1]: plt.xlabel('Pos X')
        if spy == 0: plt.title('B:35 G:70 R:105')
        yl = plt.ylim()
        ymin = min(yl[0],ymin)
        ymax = max(yl[1],ymax)
        
        # plot driven firing rate by pos_y by size_x : subplot 3
        plt.subplot(subplots_height, subplots_width, spy * subplots_width + 3)
        logging.debug("Subplot: %i" % (spy * subplots_width + 3))
        plot_rate(stimtimer, systimes[stimid], 'pos_y', 'size_x', groupedSpikes[spikegroup], 0, options.after, tb, baseline)
        if spikegroup == spikegroupI[-1]: plt.xlabel('Pos Y')
        if spy == 0: plt.title('B:35 G:70 R:105')
        yl = plt.ylim()
        ymin = min(yl[0],ymin)
        ymax = max(yl[1],ymax)
    
    for i in xrange(subplots_width * subplots_height):
        # set ylimits for all plots
        plt.subplot(subplots_height,subplots_width,i+1)
        plt.ylim([ymin,ymax])
    
    # plt.show()
    plt.savefig("%s/%s_%i_driven_rate.pdf" % (outDir, options.spikegroup[:-1], spikegroup))
    plt.clf()

resultsFile.close()
