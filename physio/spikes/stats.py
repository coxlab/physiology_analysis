#!/usr/bin/env python

#import logging

import numpy as np


def waveform_snr(waveform, bounds=(30, 70)):
    rms = lambda x: np.sqrt(np.sum(x ** 2.) / len(x))
    return (rms(waveform[bounds[0]:bounds[1]]) / \
            rms(waveform[:bounds[0]])) ** 2.


def waveform_snr2(waveform, bounds=(30, 70)):
    return np.mean(waveform[bounds[0]:bounds[1]]) / \
            np.std(waveform[:bounds[0]])


def waveforms_snr(waveforms, bounds=(30, 70)):
    if len(waveforms) == 0:
        return 0.0

    wf_arr = np.array(waveforms)
    mean_wf = np.mean(wf_arr, 0)
    sig = max(abs(mean_wf[bounds[0]:bounds[1]]))

    return sig / np.std(wf_arr[:, 0:bounds[0]])


def xcorr(a, b, margin=44):
    if len(a) == 0 or len(b) == 0:
        return 0.
    dt = np.array([b[np.abs(b - i).argmin()] - i for i in a])
    if len(dt) == 0:
        return 0.
    th = dt[np.abs(dt) < margin]  # plot only dt near 0
    return len(th) / float(len(a))


def event_lock(eventTimes, spikeTimes, preT, postT, unpack=False):
    """
    Parameters
    ----------
    unpack : bool
        Return locked spike times as a 1d array
    """
    allspikes = []
    for et in eventTimes:
        spikes = spikeTimes[(spikeTimes > (et + preT)) & \
                (spikeTimes < (et + postT))] - et
        allspikes.append(spikes)

    if unpack:
        return np.hstack(allspikes)
    else:
        return allspikes


def binned_rate(eventTimes, spikeTimes, preT, postT):
    binnedTimes = event_lock(eventTimes, spikeTimes, preT, postT, unpack=True)
    return len(binnedTimes) / float(len(eventTimes))


def spontaneous_rate(eventTimes, spikeTimes, preT=-0.1):
    return binned_rate(eventTimes, spikeTimes, preT, 0.)
