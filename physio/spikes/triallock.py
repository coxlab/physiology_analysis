#!/usr/bin/env python

import numpy

import latency


def bin_response(spikes, trials, prew, duration, binw, raw=False):
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
    M = numpy.empty((0, nbins))
    for trial in trials:
        start = trial - prew
        end = trial + duration
        ts = spikes[numpy.logical_and(spikes > start, spikes <= end)] \
                - trial
        M = numpy.vstack((M, numpy.histogram(ts, bins=bins)[0]))
    m = numpy.mean(M, 0)
    s = numpy.std(M, 0)
    if raw:
        return m, s, M
    return m, s


def window_response(spike_times, trial_times, windows, raw_counts=False):
    """
    spike_times : array of floats
    trial_times : array of floats
    windows : list of 2 tuples of (start, stop) times [non-inclusive]
    raw : bool
        return raw counts of type ndarray, shape(len(windows), len(trials)

    returns
    -----
    rates : array of floats
        spike rates per window
    """
    assert(type(spike_times) == numpy.ndarray)
    counts = numpy.empty((len(windows), len(trial_times)))
    for (ti, tt) in enumerate(trial_times):
        for (wi, w) in enumerate(windows):
            start = tt + w[0]
            end = tt + w[1]
            counts[wi, ti] = numpy.sum( \
                    numpy.logical_and(spike_times > start, \
                    spike_times < end))
    if raw_counts:
        return counts
    # convert to rates
    wls = numpy.array([1. / (w[1] - w[0]) for w in windows])
    return numpy.mean(counts, 1) * wls


def rate_per_trial(spike_times, trial_times, windows):
    counts = window_response(spike_times, trial_times, \
            windows, raw_counts=True)
    wls = numpy.array([1. / (w[1] - w[0]) for w in windows])
    wls = wls.reshape(len(windows), 1)
    return wls * counts


def find_significant_bins(spikes, trials, duration, binw, alpha=0.001):
    _, _, M = bin_response(spikes, trials, binw, duration, binw, raw=True)
    # add 1 to offset for baseline bin
    return latency.measure_binned_latency(M[:, 0], M[:, 1:], alpha) + 1
