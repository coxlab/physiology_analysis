import caton_utils
import mw_utils
import os
import matplotlib.pylab as plt

base_path = "/Volumes/Data/physiology/" 
h5_file = os.path.join(base_path, 
                "H8_110425/processed.safe/session_1_3699_to_5410_a32_batch/session_1_3699_to_5410_a32_batch.h5")
mw_file = os.path.join(base_path, "H8_110425.mwk")

print("Loading from h5")
(clusters, times, triggers, waveforms) = caton_utils.extract_info_from_h5(h5_file)

print("Loading from MW")
grouped_stim_times = mw_utils.extract_and_group_stimuli(mw_file, time_offset=3699+486.026384)

aggregated_stim_times = mw_utils.aggregate_stimuli(grouped_stim_times)

spike_trains_by_channel = caton_utils.spikes_by_cluster(times, clusters)

plt.ioff()
plt.figure()

f = plt.figure()

nchannels = len(spike_trains_by_channel)
nstim = len(grouped_stim_times.keys())
stim_keys = grouped_stim_times.keys()


 
    
for stim in range(0, len(stim_keys)):
    stim_key = stim_keys[stim]

    if stim_key is "pixel clock" or \
       stim_key is "background" or \
       stim_key is "BlankScreenGray":
       continue

    for ch in range(1, len(spike_trains_by_channel)):
        
        print("Plotting cl %d, stim %s" % (ch, stim_key))
        
        # plt.subplot( nchannels, nstim, ch *nstim + stim)
        
        ev_locked = mw_utils.event_lock_spikes( grouped_stim_times[stim_key], 
                                                spike_trains_by_channel[ch], 0.1, 0.5 )
        mw_utils.plot_rasters(ev_locked)
        plt.title("clu %d, stim %s" % (ch, stim_key))
        plt.savefig("figures/clusters/clu%d_stim%s.pdf" % (ch, stim_key))
        plt.hold(False)
        plt.clf()
