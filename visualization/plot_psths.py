#!/usr/bin/env python

import logging, optparse, sys
logging.basicConfig(level = logging.DEBUG)

import numpy as np
import pylab as pl

import physio

parser = optparse.OptionParser(usage="usage: %prog [options] session")
parser.add_option("-g", "--group", dest="group", default="name",
                    help="Group stimuli by this variable: name, pos_x, pos_y, size_x...")
parser.add_option("-b", "--before", dest="before", default=-0.25,
                    help="Seconds before stimulus onset to plot")
parser.add_option("-a", "--after", dest="after", default=0.75,
                    help="Seconds after stimulus onset to plot")
parser.add_option("-n", "--nbins", dest="nbins", default=20,
                    help="Number of bins in histogram")
parser.add_option("-c", "--channel", dest="channel", default=7,
                    help="Channel to plot")

(options, args) = parser.parse_args()
if len(args) != 1:
    parser.print_usage()
    sys.exit(1)

# plotWindow = [-0.25, .75]
# plotNBins = 20
# channel = 7
# group = 'name'
# nChannels = 32
# depthOrdered = physio.channelmapping.position_to_tdt(range(nChannels))

session = physio.session.load(args[0])#'K4_110720')
# session = physio.session.load('K4_110830')



trialTimes, stimuli, _, _ = session.get_trials()
nTrials = len(trialTimes)
logging.debug("N Trials: %i" % nTrials)

stimCounts = physio.events.stimuli.count(stimuli)
uniqueStimuli = physio.events.stimuli.unique(stimuli)
for s in stimCounts.keys():
    logging.debug("\t%i presentations of %s" % (stimCounts[s],s))

# get unique positions & sizes
values = []
for s in uniqueStimuli:
    values[s[options.group]] = 1
values = sorted(values.keys())
# pxs = {}
# pys = {}
# sizes = {}
# names = {}
# for s in uniqueStimuli:
#     pxs[s['pos_x']] = 1
#     pys[s['pos_y']] = 1
#     sizes[s['size_x']] = 1
#     names[s['name']] = 1
# names = sorted(names.keys())
# pxs = sorted(pxs.keys())
# pys = sorted(pys.keys())
# sizes = sorted(sizes.keys())

# generate x & y arrays
# 120 total :-O
#[name, :], [name, px, py[1], :], [name, px[1], py, :], [name, size, :]
conditions = []
for v in values:
    conditions.append({condition : v})
# for n in names:
#     conditions.append({'name' : n})
# conditions = uniqueStimuli
# data = [(ch,cl) for ch in depthOrdered for cl in range(1,6)]
data = [(options.channel, cl) for cl in range(1,6)]


subplotsWidth = len(conditions)
subplotsHeight = len(data)
pl.figure(figsize=(subplotsWidth*2, subplotsHeight*2))
# pl.gcf().suptitle('%s %d' % (groupBy, group))
pl.subplot(subplotsHeight, subplotsWidth,1)
logging.debug("Plotting %i by %i plots(%i)" % (subplotsWidth, subplotsHeight, subplotsWidth * subplotsHeight))

ymaxs = [0 for i in data]
for (y, datum) in enumerate(data):
    for (x, condition) in enumerate(conditions):
        logging.debug("\tPlotting[%i, %i]: ch/cl %s : s %s" % (x, y, datum, condition))
        trials, _, _, _ = session.get_trials(condition)
        spikes = session.get_spike_times(*datum)
        pl.subplot(subplotsHeight, subplotsWidth, subplotsWidth * y + x + 1)
        physio.plotting.psth.plot(trials, spikes, options.before, options.after, options.nbins)
        pl.axvline(0., color = 'k')
        pl.axvspan(0., 0.5, color = 'k', alpha = 0.1)
        
        if x == 0:
            pl.ylabel('Cluster: %i\nRate(Hz)' % datum[1])
        else:
            pl.yticks([])
        if y == 0: pl.title('%s' % str(condition), rotation=45)
        if y < len(data) - 1:
            pl.xticks([])
        else:
            pl.xticks([0., .5])
            pl.xlabel("Seconds")
        ymaxs[y] = max(ymaxs[y], pl.ylim()[1])

session.close()

for y in xrange(subplotsHeight):
    for x in xrange(subplotsWidth):
        pl.subplot(subplotsHeight, subplotsWidth, subplotsWidth * y + x + 1)
        pl.ylim(0,ymaxs[y])
        
pl.savefig("psth_%i_%s.png" % (options.channel, options.group))