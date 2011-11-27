#!/usr/bin/env python

import logging, optparse, os, sys, time
logging.basicConfig(level = logging.DEBUG)
#import matplotlib
import numpy as np
import pylab as pl
import scipy.stats

import physio

snrw = (30,70)
bwin = (-0.2, 0)
rwin = (0.05, 0.2)

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

def group_by_stimuli(spikes_by_trials, stimuli, key):
    grouped = {}
    all_key_vals = [s[key] for s in stimuli]
    def unique(x):
        return sorted(set(x))
    unique_key_vals = unique(all_key_vals)
    
    for k in unique_key_vals:
        grouped[k] = []
    
    for (i, spikes) in enumerate(spikes_by_trials):
        keyval = stimuli[i][key]
        grouped[keyval].append(spikes)

    return grouped

def get_responsivity(session, ch, cl, bwin=(-0.2,0), rwin=(0.05,0.15)):
    return get_selectivity(session, ch, cl, bwin, rwin, True)
    
def get_selectivity(session, ch, cl, bwin=(-0.2,0), rwin=(0.05,0.15),
                    include_baseline_condition=False):
    spikes = session.get_spike_times(ch, cl)
    trial_times, stimuli, _, _ = session.get_trials()
    #trial_times, stimuli, _, _ = session.get_gaze_filtered_trials()
    
    if len(spikes) == 0 or len(trial_times) == 0:
        return 0,0,0,0,0,0
    
    cull_half = False
    if cull_half:
        st = len(trial_times)/2
        trial_times = trial_times[st:]
        stimuli = stimuli[st:]
    
    spikes_by_trials = physio.spikes.stats.event_lock(trial_times, spikes, 
                                                      rwin[0], rwin[1])
    
    baseline_spikes = physio.spikes.stats.event_lock(trial_times, spikes,
                                                         bwin[0], bwin[1])
    
    grouped = group_by_stimuli(spikes_by_trials, stimuli, 'name')
    stim_names = grouped.keys()
    
    stim_names.sort()
    
    all_rates = []
    all_means = []
    all_medians = []
    all_sqrt_counts = []
    
    for n in stim_names:
        trial_spikes = grouped[n]
        counts = [len(s) for s in trial_spikes]
        rates = [c / (rwin[1]-rwin[0]) for c in counts]
        
        all_rates.append(rates)
        all_sqrt_counts.append(np.sqrt(np.array(counts) + 1))
        all_means.append(np.mean(np.array(rates)))
        all_medians.append(np.median(np.array(rates)))
    
    if include_baseline_condition:
        baseline_counts = [len(s) for s in baseline_spikes]
        baseline_rates = [c / (rwin[1]-rwin[0]) for c in baseline_counts]
        all_rates.append(baseline_rates)
    
    print all_means
    print all_medians
    print stim_names
    
    H = F = X = 0
    p = p2 = p3 = 0
    
    try:
        H, p = scipy.stats.kruskal(*all_rates)
        print ("kruskal H=%f, p=%f" % (H, p))
    except Exception as e:
        print(e)
    
    try:
        F, p2 = scipy.stats.f_oneway(*all_sqrt_counts)
        print ("anova F=%f, p=%f" % (F, p2))
    except Exception as e:
        print(e)
    
    try:
        lens = [len(r) for r in all_rates]
        trunced = [np.array(r[0:np.min(lens)]) for r in all_rates]
        X, p3 = scipy.stats.friedmanchisquare(*trunced)
        print ("friedman=%f, p=%f" % (X, p3))
    except Exception as e:
        print(e)
    
    return (H, p, F, p2, X, p3)

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
        #for ch in [6]:
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
                
                rH,rp1,rF,rp2,rX,rp3  = get_responsivity(session, ch, cl, bwin, rwin)
                H,p1,F,p2,X,p3 = get_selectivity(session, ch, cl, bwin, rwin)
                
                summaryFile.write("%s %i %i %i %i %i %f %f %f %f %f %i %f %f %f %f %f %f %f %f %f %f %f %f\n" %\
                    (goodSession, epochNumber, timerange[0], timerange[1], 
                      ch, cl, location[0], location[1], location[2], 
                      meansnr, stdsnr, nspikes, rate, brate, drate,
                      rp1, rp2, rp3, H, p1, F, p2, X, p3))
                print goodSession, epochNumber, timerange[0], timerange[1], ch, cl, location[0], location[1], location[2], meansnr, stdsnr, nspikes, rate, brate, drate
                summaryFile.flush()
                toc = time.time() - tic
                logging.debug("%f seconds to compute report metrics" % (toc))
        session.close()

summaryFile.close()
# save this somewhere
