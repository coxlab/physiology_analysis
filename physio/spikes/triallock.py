#!/usr/bin/env python

import numpy

import latency

def bin_response(spikes, trials, prew, duration, binw, raw = False):
    """
    Parameters
    ----------
    spikes : array of spike times
    trials : array of trial start times
    prew : pre trial period (in seconds) to capture
    duration : length of trial/stimulus & post start time to capture
    binw : length of bin in seconds
    raw : flag (default = False); return raw response matrix
    """
    nbins = int((duration + prew) / binw)
    bins = numpy.linspace(-prew, duration, nbins + 1)
    M = numpy.empty((0,nbins))
    for trial in trials:
        start = trial - prew
        end = trial + duration
        ts = spikes[numpy.logical_and(spikes > start, spikes <= end)] \
                - trial
        M = numpy.vstack((M, numpy.histogram(ts, bins = bins)[0]))
    m = numpy.mean(M, 0)
    s = numpy.std(M, 0)
    if raw:
        return m, s, M
    return m, s

def find_significant_bins(spikes, trials, duration, binw, alpha = 0.001):
    _, _, M = bin_response(spikes, trials, binw, duration, binw, raw = True)
    # add 1 to offset for baseline bin
    return latency.measure_binned_latency(M[:,0], M[:,1:], alpha) + 1
