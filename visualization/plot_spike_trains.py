#!/usr/bin/env python

import logging
import os
import sys
logging.basicConfig(level = logging.DEBUG)

#import numpy as np
import pylab as pl

import physio

# parse command line options
#parser = argparse.ArgumentParser()
#parser.add_argument("session")
#parser.add_argument("epoch", default=None)

#args = parser.parse_args()
if len(sys.argv) < 2:
    raise ValueError("Must supply session: script.py <session>")
    sys.exit(1)
session_name = sys.argv[1]

config = physio.cfg.load(session_name)

if len(sys.argv) < 3:
    epochs = range(physio.session.get_n_epochs(session_name))#config))
else:
    epochs = [int(sys.argv[2]),]

#session_name = args.session

for epochNumber in epochs:
    session = physio.session.load(session_name, epochNumber)
    outdir = physio.session.get_epoch_dir(config, epochNumber) + '/plots'

    #trialTimes, stims = session.get_stimuli(stimType = 'image')
    #nTrials = len(trialTimes)
    time_range = session.get_epoch_time_range('au')
    pl.figure(1, figsize=(8,16))
    pl.axvline(time_range[0], color='k')
    pl.axvline(time_range[1], color='k')

    max_n_clusters = max([session.get_n_clusters(ch) for\
            ch in range(1,33)])

    cmap = pl.cm.Paired

    dy = 1/float(max_n_clusters-1)
    for ch in xrange(1,33):
        n_clusters = session.get_n_clusters(ch)
        if ch % 2: # highlight every other channel
            pl.bar(time_range[0], 1, time_range[1]-time_range[0], ch,\
                    color = 'k', alpha=0.2, linewidth = 0)
        for cl in xrange(n_clusters):
            spikes = session.get_spike_times(ch, cl)
            if len(spikes) == 0: continue

            c = cmap(cl * dy)
            pl.bar(spikes[0], dy, spikes[-1]-spikes[0], ch + dy * cl,\
                    color = c, linewidth = 0)
        lx = time_range[0] - 10
        ly = ch + .5
        pl.text(lx, ly, "%i" % ch, ha='right', va='center')

    # TODO make sensible axes
    pl.xlabel("Time (Seconds, audio)")
    pl.yticks([])
    pl.ylim([1,33])
    session.close()

    if not os.path.exists(outdir): os.makedirs(outdir)
    pl.savefig("%s/spike_ranges.png" % (outdir))
