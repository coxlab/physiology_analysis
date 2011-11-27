#!/usr/bin/env python

import logging, optparse, os, sys, time
logging.basicConfig(level = logging.DEBUG)
#import matplotlib
import numpy as np
import pylab as pl

import physio

snrw = (30,70)
bwin = (-0.2, 0)
rwin = (0.05, 0.15)

cfg = physio.cfg.Config()
cfg.read_user_config()

goodSessions = physio.session.get_valid_sessions(cfg)

summaryFile = open('summaryfile','w')

def get_baseline_and_driven_rate(session, ch, cl, bwin = (-0.2,0), rwin = (0.05, 0.15)):
    spikes = session.get_spike_times(ch, cl)
    trialTimes, stimuli, _, _ = session.get_trials()
    targetTimes, blueStimuli = session.get_stimuli(stimType = 'rectangle')
    allStimTimes = trialTimes + targetTimes
    assert len(trialTimes) + len(targetTimes) == len(allStimTimes)
    #print len(allStimTimes), len(spikes), ch, cl

    # get baseline firing rate
    bspikes = sum([len(s) for s in physio.spikes.stats.event_lock(allStimTimes, spikes, bwin[0], bwin[1])])
    brate = bspikes / (float(bwin[1] - bwin[0]) * len(allStimTimes))
    #print bspikes, brate
    
    # get driven rate to all stimuli
    dspikes = sum([len(s) for s in physio.spikes.stats.event_lock(allStimTimes, spikes, rwin[0], rwin[1])])
    drate = dspikes / (float(rwin[1] - rwin[0]) * len(allStimTimes))
    #print dspikes, drate
    return brate, drate

def get_rate(session, ch, cl, condition, rwin = (0.05, 0.15)):
    spikes = session.get_spike_times(ch, cl)
    trials, _, _, _ = session.get_trials(condition)
    if len(trials) == 0:
        raise ValueError("no trials for condition: %s" % str(condition))
    s = [len(ts) for ts in physio.spikes.stats.event_lock(trials, spikes, rwin[0], rwin[1])]
    ms = pl.mean(s) / (float(rwin[1] - rwin[0]))
    ss = pl.std(s) / (float(rwin[1] - rwin[0]) * pl.sqrt(len(s)))
    nt = len(s)
    return ms, ss, nt

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
                tic = time.time()
                waves = session.get_spike_waveforms(ch, cl)
                snr = physio.spikes.stats.waveforms_snr(waves, snrw)
                meansnr = snr
                stdsnr = np.nan
                #snrs = pl.array([physio.spikes.stats.waveform_snr2(w, snrw) for w in waves])
                #meansnr = pl.mean(snrs)
                #stdsnr = pl.std(snrs)
                nspikes = len(waves)
                timerange = session.get_epoch_time_range('audio') # tuple (start, end)
                rate = nspikes/float(timerange[1] - timerange[0])
                brate, drate = get_baseline_and_driven_rate(session, ch, cl, bwin, rwin)
                summaryFile.write("%s %i %i %i %i %i %f %f %f %f %f %i %f %f %f\n" %\
                    (goodSession, epochNumber, timerange[0], timerange[1], ch, cl, location[0], location[1], location[2], meansnr, stdsnr, nspikes, rate, brate, drate))
                print goodSession, epochNumber, timerange[0], timerange[1], ch, cl, location[0], location[1], location[2], meansnr, stdsnr, nspikes, rate, brate, drate
                summaryFile.flush()
                toc = time.time() - tic
                logging.debug("%f seconds to compute report metrics" % (toc))
        session.close()

summaryFile.close()
# save this somewhere
