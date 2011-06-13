#!/usr/bin/env python

# add path of physio module
import sys
sys.path.append('../')

from physio import caton_utils
from physio import mw_utils
import os
import matplotlib.pylab as plt

base_path = "../data/K4_110523/"
h5_file = os.path.join(base_path, 
                "processed/session_1_1017_to_4412_a32_batch/session_1_1017_to_4412_a32_batch.h5")
mw_file = os.path.join(base_path, "K4_110523.mwk")

print("Loading from h5")
(clusters, times, triggers, waveforms) = caton_utils.extract_info_from_h5(h5_file)

print("Loading from MW")
# this offset is the mw time at the start of the clustering analysis
grouped_stim_times = mw_utils.extract_and_group_stimuli(mw_file, time_offset=2675.8280759999998)

aggregated_stim_times = mw_utils.aggregate_stimuli(grouped_stim_times)

spike_trains_by_channel = caton_utils.spikes_by_channel(times, triggers)

plt.ioff()
plt.figure()

f = plt.figure()

nchannels = len(spike_trains_by_channel)
nstim = len(grouped_stim_times.keys())
stim_keys = grouped_stim_times.keys()

figure_dir = '../figures'
if not os.path.exists(figure_dir): os.makedirs(figure_dir)

for stim in range(0, len(stim_keys)):
    stim_key = stim_keys[stim]
    
    if stim_key in ['pixel clock', 'background', 'BlankScreenGray']:
        continue
    
    for ch in range(0, len(spike_trains_by_channel)):
        
        print("Plotting ch %d, stim %s" % (ch, stim_key))
        
        # plt.subplot( nchannels, nstim, ch *nstim + stim)
        
        ev_locked = mw_utils.event_lock_spikes( grouped_stim_times[stim_key], 
                                                spike_trains_by_channel[ch], 0.1, 0.5 )
        mw_utils.plot_rasters(ev_locked)
        plt.title("ch %d, stim %s" % (ch, stim_key))
        plt.savefig("%s/ch%d_stim%s.pdf" % (figure_dir, ch, stim_key))
        plt.hold(False)
        plt.clf()
