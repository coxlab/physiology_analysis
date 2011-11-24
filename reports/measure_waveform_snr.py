#!/usr/bin/env python

import logging, optparse, os, sys
logging.basicConfig(level = logging.DEBUG)
#import matplotlib
import numpy as np
import pylab as pl

import physio

snrw = (30,70)

cfg = physio.cfg.Config()
cfg.read_user_config()

goodSessions = physio.session.get_valid_sessions(cfg)

summaryFile = open('summaryfile','w')

for goodSession in goodSessions:
    cfg = physio.cfg.Config()
    cfg.read_user_config()
    cfg.read_session_config(goodSession)
    cfg.set_session(goodSession)
    for epochNumber in xrange(physio.session.get_n_epochs(cfg)):
        session = physio.session.load(goodSession, epochNumber)
        try:
            locations = session.get_channel_locations()
        except Exception as E:
            logging.warning("Location calculation failed for session %s epoch %i" % (goodSession, epochNumber))
            logging.warning(str(E))
            locations = np.zeros((32,3))
        for ch in xrange(1,33):
            location = locations[ch-1]
            for cl in xrange(session.get_n_clusters(ch)):
                waves = session.get_spike_waveforms(ch, cl)
                snrs = pl.array([physio.spikes.stats.waveform_snr(w, snrw) for w in waves])
                meansnr = pl.mean(snrs)
                stdsnr = pl.std(snrs)
                nspikes = len(snrs)
                timerange = session.get_epoch_time_range('audio') # tuple (start, end)
                rate = nspikes/float(timerange[1] - timerange[0])
                summaryFile.write("%s %i %i %i %i %i %f %f %f %f %f %i %f\n" %\
                    (goodSession, epochNumber, timerange[0], timerange[1], ch, cl, location[0], location[1], location[2], meansnr, stdsnr, nspikes, rate))
                print goodSession, epochNumber, timerange[0], timerange[1], ch, cl, location[0], location[1], location[2], meansnr, stdsnr, nspikes, rate
                summaryFile.flush()
        session.close()

summaryFile.close()
# save this somewhere
