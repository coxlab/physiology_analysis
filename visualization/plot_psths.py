#!/usr/bin/env python

import logging, optparse, os, sys
logging.basicConfig(level = logging.DEBUG)

import physio

import numpy as np
import pylab as pl


parser = optparse.OptionParser(usage="usage: %prog [options] session")
parser.add_option("-g", "--group", dest="group", default="name",
                    help="Group stimuli by this variable: name, pos_x, pos_y, size_x...", type='str')
parser.add_option("-b", "--before", dest="before", default=-0.25,
                    help="Seconds before stimulus onset to plot", type='float')
parser.add_option("-a", "--after", dest="after", default=0.75,
                    help="Seconds after stimulus onset to plot", type='float')
parser.add_option("-n", "--nbins", dest="nbins", default=20,
                    help="Number of bins in histogram", type='int')
parser.add_option("-c", "--channel", dest="channel", default=7,
                    help="Channel to plot", type='int')
parser.add_option("-o", "--outdir", dest="outdir", default="",
                    help="Output directory", type='str')
parser.add_option("-t", "--gaze_std_thresh", dest="gaze_std_thresh", 
                  type='float', default=0.0, 
                  help="Threshold for trial-wise gaze std for inclusion")
parser.add_option("-d", "--gaze_default_dev_thresh", dest="gaze_dev_thresh", 
                  type='float', default=0.0, 
                  help="Threshold for trial-wise deviation of gaze from the 'default'")

(options, args) = parser.parse_args()
if len(args) < 1:
    parser.print_usage()
    sys.exit(1)


process_gaze = (options.gaze_std_thresh > 0.0 or options.gaze_dev_thresh > 0.0)
    

config = physio.cfg.load(args[0])

epochs = []
if len(args) == 2:
    epochs = [int(args[1])]
else:
    epochs =  range(physio.session.get_n_epochs(config))

for epochNumber in epochs:
    session = physio.session.load(args[0], epochNumber)
    if True or options.outdir.strip() == '':
        config = physio.cfg.load(args[0])
        outdir = physio.session.get_epoch_dir(config, epochNumber)
        # outdir = config.get('session','output')
        outdir += '/plots'
        options.outdir = outdir

    trialTimes, stimuli, _, _ = session.get_trials()
    nTrials = len(trialTimes)
    logging.debug("N Trials: %i" % nTrials)

    stimCounts = physio.events.stimuli.count(stimuli)
    uniqueStimuli = physio.events.stimuli.unique(stimuli)
    for s in stimCounts.keys():
        logging.debug("\t%i presentations of %s" % (stimCounts[s],s))

    # get unique positions & sizes
    values = {}
    for s in uniqueStimuli:
        values[s[options.group]] = 1
    values = sorted(values.keys())

    conditions = []
    for v in values:
        conditions.append({options.group : v})

    nclusters = session.get_n_clusters(options.channel)
    clusters = range(0,nclusters)
    data = [(options.channel, cl) for cl in clusters]


    subplotsWidth = len(conditions)
    subplotsHeight = len(data)
    pl.figure(figsize=(subplotsWidth*2, subplotsHeight*2))

    pl.subplot(subplotsHeight, subplotsWidth,1)
    logging.debug("Plotting %i by %i plots(%i)" % (subplotsWidth, subplotsHeight, subplotsWidth * subplotsHeight))


    ymaxs = [0 for i in data]
    for (y, datum) in enumerate(data):
        for (x, condition) in enumerate(conditions):
            logging.debug("\tPlotting[%i, %i]: ch/cl %s : s %s" % (x, y, datum, condition))
            
            if process_gaze:
                trials, _, _, _ = session.get_gaze_filtered_trials(
                                          condition,
                                          intra_trial_std_threshold=options.gaze_std_thresh,
                                          default_gaze_deviation_threshold=options.gaze_dev_thresh)
            else:
                trials, _, _, _ = session.get_trials(condition)
            
            # as a hack / test, just take the second half:
            # trials = trials[len(trials)/3:]
            
            
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

    if not os.path.exists(options.outdir): os.makedirs(options.outdir) # TODO move this down
    pl.savefig("%s/psth_%i_%s.png" % (options.outdir, options.channel, options.group))
