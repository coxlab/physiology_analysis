#!/usr/bin/env python

import logging

import numpy as np

def xcorr(a, b, margin=44):
    if len(a) == 0 or len(b) == 0: return 0.
    dt = np.array([b[np.abs(b - i).argmin()] - i for i in a])
    if len(dt) == 0: return 0.
    th = dt[np.abs(dt) < margin] # plot only dt near 0
    return len(th) / float(len(a))

def event_lock(eventTimes, spikeTimes, preT, postT, unpack = False):
    """
    Parameters
    ----------
    unpack : bool
        Return locked spike times as a 1d array
    """
    allspikes = []
    for et in eventTimes:
        spikes = spikeTimes[(spikeTimes > (et + preT)) & (spikeTimes < (et + postT))] - et
        allspikes.append(spikes)
    
    if unpack:
        return np.hstack(allspikes)
    else:
        return allspikes

def binned_rate(eventTimes, spikeTimes, preT, postT):
    binnedTimes = event_lock(eventTimes, spikeTimes, preT, postT, unpack = True)
    return len(binnedTimes) / float(len(eventTimes))

def spontaneous_rate(eventTimes, spikeTimes, preT = -0.1):
    return binned_rate(eventTimes, spikeTimes, preT, 0.)

# # --------------------- OLD ---------------------
# 
# import channel_mapping
# import mw_utils
# 
# def find_multi_channel_spikes_indexes(triggers):
#     """
#     Return indexes of spikes that triggered on more than one channel.
#     """
#     return np.where(np.sum(triggers,1) != 1)[0]
# 
# def find_single_channel_spike_indexes(triggers):
#     """
#     Return indexes of spikes that triggered on only one channel
#     """
#     return np.where(np.sum(triggers,1) == 1)[0]
# 
# def single_channel_triggers_to_channels(triggers):
#     """
#     Convert single channel triggers to channel indexes
#     ONLY works for single channel spikes
#     """
#     return np.sum(np.array(triggers) * np.arange(32),1)
# 
# def find_good_channel_spike_indexes(channels, bad_nn_channels):
#     """
#     Return indexes for spikes that occurred on 'good' channels
#     """
#     logging.debug("Cleaning bad nn channels: %s" % str(bad_nn_channels))
#     bad_channels = channel_mapping.neuronexus_to_audio(bad_nn_channels)
#     logging.debug("Found bad audio channels: %s" % str(bad_channels))
#     good_indexes = None
#     for ch in xrange(32):
#         if not (ch in bad_channels):
#             if good_indexes is None:
#                 good_indexes = np.where(channels == ch)[0]
#             else:
#                 good_indexes = np.hstack((good_indexes, np.where(channels == ch)[0]))
#     return good_indexes
# 
# def compute_spontaneous_rate(stim_times, spike_times, time_base, pre_time=0.1):
#     non_stim_spikes = mw_utils.event_lock_spikes(stim_times, spike_times, pre_time, 0)
#     return len(non_stim_spikes) / float(len(stim_times))
# 
# def clean_spikes(times, clusters, triggers, bad_nn_channels, waveforms=None):
#     good_spikes = find_single_channel_spike_indexes(triggers)
#     logging.debug("Spikes on single channels: %s" % len(good_spikes))
#     
#     times = np.array(times)[good_spikes]
#     clusters = np.array(clusters)[good_spikes]
#     triggers = np.array(triggers)[good_spikes]
#     if not (waveforms is None):
#         waveforms = np.array(waveforms)[good_spikes]
#     
#     channels = single_channel_triggers_to_channels(triggers)
#     good_spikes = find_good_channel_spike_indexes(channels, bad_nn_channels)
#     logging.debug("Spikes on single good channels: %s" % len(good_spikes))
#     
#     times = np.array(times)[good_spikes]
#     clusters = np.array(clusters)[good_spikes]
#     triggers = np.array(triggers)[good_spikes]
#     if not (waveforms is None):
#         waveforms = np.array(waveforms)[good_spikes]
#         return times, clusters, triggers, waveforms
#     else:
#         return times, clusters, triggers