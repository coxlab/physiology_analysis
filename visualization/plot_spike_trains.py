#!/usr/bin/env python

import logging
import argparse
import os
import sys
logging.basicConfig(level = logging.DEBUG)

import numpy as np
import pylab as pl

import physio

# parse command line options
parser = argparse.ArgumentParser()
parser.add_option("session")
parser.add_option("epoch", default=None)

args = parser.parse_args()

config = physio.cfg.load(args.session)

if args.epoch is None:
    epochs = range(physio.session.get_n_epochs(config))
else:
    epochs = [int(args.epoch),]

session_name = args.session

for epochNumber in epochs:
    session = physio.session.load(session_name, epochNumber)
    outdir = physio.session.get_epoch_dir(config, epochNumber) + '/plots'

    #trialTimes, stims = session.get_stimuli(stimType = 'image')
    #nTrials = len(trialTimes)
    time_range = session.get_epoch_time_range('au')
    pl.figure(1, figsize=(8,8))
    pl.axvline(time_range[0], color='k')
    pl.axvline(time_range[1], color='k')

    max_n_clusters = max([session.get_n_clusters(ch) for\
            ch in range(1,33)])

    cmap = pl.cm.Paired

    for ch in xrange(1,33):
        n_clusters = session.get_n_clusters(ch)
        for cl in xrange(n_clusters):

            dy = cl/float(n_clusters-1)
            color = cmap(cl/float(max_n_clusters-1))

            spikes = session.get_spike_times(ch, cl)

            dy = cl/float(n_clusters-1)
            c = cmap(cl/float(max_n_clusters-1))
            pl.bar(spikes[0], dy, spikes[-1]-spikes[0], ch,\
                    color = c, linewidth = 0)

    # TODO make sensible axes
    session.close()

    if not os.path.exists(outdir): os.makedirs(outdir)
    pl.savefig("%s/spike_ranges.png" % (outdir))
