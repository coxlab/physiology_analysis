#!/usr/bin/env python

import logging
import optparse
import os
import sys
logging.basicConfig(level=logging.DEBUG)

import numpy
import pylab

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
    epochs = [int(args[1]), ]
else:
    epochs = range(physio.session.get_n_epochs(args[0]))  # config))

for epochNumber in epochs:
    #session = physio.session.load(args[0], epochNumber)
    summary = physio.summary.load_summary(args[0], epochNumber)
    if True or options.outdir.strip() == '':
        #config = physio.cfg.load(args[0])
        outdir = physio.session.get_epoch_dir(config, epochNumber)
        # outdir = config.get('session','output')
        outdir += '/plots'
        options.outdir = outdir

    match = {'name': 'BlueSquare'}
    trials = summary.get_trials(match)
    trialTimes = numpy.array(trials['time'])
    #trialTimes, stims = session.get_stimuli(stimType='rectangle')
    nTrials = len(trialTimes)
    logging.debug("N Trials: %i" % nTrials)

    channels = range(1, 33)
    #nclusters = [session.get_n_clusters(ch) for ch in channels]
    nclusters = [summary.get_n_clusters(ch) for ch in channels]
    nclusters = min(10, max(nclusters))
    clusters = range(0, nclusters)

    subplotsWidth = len(channels)
    subplotsHeight = min(10, len(clusters))
    pylab.figure(figsize=(subplotsWidth * 2, subplotsHeight * 2))
    # pylab.gcf().suptitle('%s %d' % (groupBy, group))
    pylab.subplot(subplotsHeight, subplotsWidth, 1)
    pylab.subplots_adjust(left=0.025, right=0.975, \
            top=0.9, bottom=0.1, wspace=0.45)
    logging.debug("Plotting %i by %i plots(%i)" % \
            (subplotsWidth, subplotsHeight, subplotsWidth * subplotsHeight))

    for (x, channel) in enumerate(channels):
        for (y, cluster) in enumerate(clusters):
            logging.debug("\tPlotting[%i, %i]: ch %s : cl %s" \
                    % (x, y, channel, cluster))
            #spikes = session.get_spike_times(channel, cluster)
            spikes = summary.get_spike_times(channel, cluster)
            pylab.subplot(subplotsHeight, subplotsWidth, \
                    subplotsWidth * y + x + 1)
            physio.plotting.psth.plot(trialTimes, spikes, options.before, \
                    options.after, options.nbins)  # , weighted = False)
            # physio.plotting.raster.plot(trialTimes, \
            #        spikes, options.before, options.after)
            pylab.axvline(0., color='k')
            pylab.axvspan(0., 0.5, color='k', alpha=0.1)

            if x == 0:
                pylab.ylabel('Cluster: %i\nRate(Hz)' % cluster)
            #else:
            #    pylab.yticks([])
            if y == 0:
                pylab.title('Ch:%i' % channel, rotation=45)
            if y < len(clusters) - 1:
                pylab.xticks([])
            else:
                pylab.xticks([0., .5])
                pylab.xlabel("Seconds")

    #session.close()
    summary.close()

    if not os.path.exists(options.outdir):
        os.makedirs(options.outdir)  # TODO move this down
    pylab.savefig("%s/bluesquare.png" % (options.outdir))
