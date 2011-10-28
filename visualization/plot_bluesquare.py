#!/usr/bin/env python

import logging, optparse, os, sys
logging.basicConfig(level = logging.DEBUG)

import numpy as np
import pylab as pl

import physio

parser = optparse.OptionParser(usage="usage: %prog [options] session")
parser.add_option("-b", "--before", dest="before", default=-0.25,
                    help="Seconds before stimulus onset to plot", type='float')
parser.add_option("-a", "--after", dest="after", default=0.75,
                    help="Seconds after stimulus onset to plot", type='float')
parser.add_option("-n", "--nbins", dest="nbins", default=20,
                    help="Number of bins in histogram", type='int')
parser.add_option("-o", "--outdir", dest="outdir", default="",
                    help="Output directory", type='str')

(options, args) = parser.parse_args()
if len(args) < 1:
    parser.print_usage()
    sys.exit(1)

config = physio.cfg.load(args[0])

epochs = []
#epochNumber = 0
if len(args) == 2:
    #epochNumber = int(args[1])
    epochs = [int(args[1]),]
else:
    epochs = physio.session.get_n_epochs(config)

for epochNumber in epochs:
    session = physio.session.load(args[0], epochNumber)
    if options.outdir.strip() == '':
        #config = physio.cfg.load(args[0])
        outdir = physio.session.get_epoch_dir(config, epochNumber)
        # outdir = config.get('session','output')
        outdir += '/plots'
        options.outdir = outdir

    trialTimes, stims = session.get_stimuli(stimType = 'rectangle')
    nTrials = len(trialTimes)
    logging.debug("N Trials: %i" % nTrials)

    channels = range(1,33)
    nclusters = [session.get_n_clusters(ch) for ch in channels]
    clusters = range(0,max(nclusters))

    subplotsWidth = len(channels)
    subplotsHeight = len(clusters)
    pl.figure(figsize=(subplotsWidth*2, subplotsHeight*2))
    # pl.gcf().suptitle('%s %d' % (groupBy, group))
    pl.subplot(subplotsHeight, subplotsWidth,1)
    pl.subplots_adjust(left = 0.025, right = 0.975, top = 0.9, bottom = 0.1, wspace = 0.45)
    logging.debug("Plotting %i by %i plots(%i)" % (subplotsWidth, subplotsHeight, subplotsWidth * subplotsHeight))

    for (x, channel) in enumerate(channels):
        for (y, cluster) in enumerate(clusters):
            logging.debug("\tPlotting[%i, %i]: ch %s : cl %s" % (x, y, channel, cluster))
            spikes = session.get_spike_times(channel, cluster)
            pl.subplot(subplotsHeight, subplotsWidth, subplotsWidth * y + x + 1)
            physio.plotting.psth.plot(trialTimes, spikes, options.before, options.after, options.nbins)#, weighted = False)
            #physio.plotting.raster.plot(trialTimes, spikes, options.before, options.after)
            pl.axvline(0., color = 'k')
            pl.axvspan(0., 0.5, color = 'k', alpha = 0.1)
            
            if x == 0:
                pl.ylabel('Cluster: %i\nRate(Hz)' % cluster)
            #else:
            #    pl.yticks([])
            if y == 0: pl.title('Ch:%i' % channel, rotation=45)
            if y < len(clusters) - 1:
                pl.xticks([])
            else:
                pl.xticks([0., .5])
                pl.xlabel("Seconds")

    session.close()

    if not os.path.exists(options.outdir): os.makedirs(options.outdir) # TODO move this down
    pl.savefig("%s/bluesquare.png" % (options.outdir))
