#!/usr/bin/env python

import logging, os, sys

logging.basicConfig(level=logging.DEBUG)

import pylab as plt

import caton_utils
import pixel_clock
import cnc_utils
import mw_utils
import utils
import cfg
# from caton_utils import caton_cluster_data, extract_info_from_h5
# from pixel_clock import read_pixel_clock, parse_pixel_clock, read_pixel_clock_from_mw, time_match_mw_with_pc
# from cnc_utils import read_cnc_from_mw, find_stable_epochs_in_events

session = 'K4_110523'
if len(sys.argv) > !:
    session = sys.argv[1]

# read in configuration file
config = cfg.Config()
config.read_user_cfg()
config.read_session_cfg(session)
config.set_session(session)

session_dir = config.get('session','dir')

# make necessary output directories
utils.make_output_dirs(config)

# data_repo = '/Volumes/Scratch'
# session = 'K4_110523'
# base_dir = '/'.join((data_repo, session))
# # base_dir =  '/Volumes/Scratch/K4_110523'
# cache_dir = "/Volumes/Scratch/tmp/"
# mw_filename = '/'.join((base_dir, session)) + '.mwk'
# 
# if not (os.path.exists(cache_dir)): os.makedirs(cache_dir)

# ==================== match pixel clock (on whole dataset) =====================

# read_pixel_clock( project_path, file_no, cache_dir="/tmp", time_range=None): return (pc_data, fs)
# (pc_data, fs) = pixel_clock.read_pixel_clock( base_dir, 1 , cache_dir )
(pc_data, fs) = pixel_clock.read_pixel_clock(session_dir, config.get('pixel clock','output'), config.get('filesystem','tmp'))

# parse_pixel_clock(pc_data, start_time_sec, samples_per_sec,
#                       arm_threshold = 0.1, arm_timeout = 0.005, 
#                       accept_threshold = 0.3, derivative_threshold = 0.0,
#                       time_stride=0.0005, refractory_period = 0.010,
#                       event_trigger_period = 0.05,
#                       pc_y_pos_deg = None,
#                       pc_height_deg = None,
#                       screen_height_deg = None): return reconstructed_events, offset_latencies
# TODO : read pc_y_pos_deg and pc_height_deg from mworks file
(reconstructed_event, offset_latencies) = pixel_clock.parse_pixel_clock(pc_data, 0., config.getfloat('audio','samprate'), \
                                                config.getfloat('pixel clock','y'), config.getfloat('pixel clock','h'), \
                                                config.getfloat('pixel clock','screenh'))
# pc_y_pos_deg = -28
# pc_height_deg = 2.5 # TODO check this
# screen_height_deg = 137.214 # TODO can I read this from mworks?
# (reconstructed_events, offset_latencies) = pixel_clock.parse_pixel_clock(pc_data, 0., 44100, \
#                                                             pc_y_pos_deg = pc_y_pos_deg,\
#                                                             pc_height_deg = pc_height_deg,\
#                                                             screen_height_deg = screen_height_deg)
pc_codes = [e.code for e in reconstructed_events]
pc_times = [e.time for e in reconstructed_events]

# read_pixel_clock_from_mw(mw_filename, use_display_update=True): return (float_times, codes)
# (mw_times, mw_codes) = pixel_clock.read_pixel_clock_from_mw(mw_filename)
(mw_times, mw_codes) = pixel_clock.read_pixel_clock_from_mw(config.get('mworks','file'))

# time_match_mw_with_pc(pc_codes, pc_times, mw_codes, mw_times,
#                                 submatch_size = 10, slack = 0, max_slack=10,
#                                 pc_check_stride = 100, pc_file_offset= 0): return TimeBase(time_matches, pc_file_offset)
time_base = pixel_clock.time_match_mw_with_pc( pc_codes, pc_times, mw_codes, mw_times)


# ================= find stable recording epoch (using mwks file) ===============
if config.get('epochs','timeunit') == 'mworks':
    epochs = utils.read_epochs_mw(session_dir, time_base)
elif config.get('epochs','timeunit') == 'audio':
    epochs = utils.read_epochs_audio(session_dir)
else:
    logging.error("epochs timeunit: %s not valid" % config.get('epochs','timeunit'))

if len(epochs) == 0:
    logging.info("Attempting to determine epochs from mworks file: %s" % config.get('session','output'))
    cnc_dict = cnc_utils.read_cnc_from_mw(config.get('mworks','file'))
    epochs = cnc_utils.find_stable_epochs_in_events(cnc_dict) # in mw_time

# ================================ cluster epoch ================================
for epoch in epochs:
    start_mw, end_mw = epoch
    start_mw += config.getfloat('epochs','settletime')
    #start_mw += 60 * 5 # give time for electrode to settle
    time_base.audio_offset = 0.
    start_audio = time_base.mw_time_to_audio(start_mw)
    end_audio = time_base.mw_time_to_audio(end_mw)
    time_base.audio_offset = -start_audio
    
    # cluster epoch
    clusterdir = '/'.join((config.get('session','output'),'clusters'))
    epoch_dir = caton_utils.caton_cluster_data(session_dir, clusterdir, time_range=(start_audio, end_audio))
    
    # TODO save time_base and start/end times
    
    # ======================= generate plots for epoch ==========================
    # TODO this data<->filename association is too opaque
    session_name = 'session_%d_to_%d_a32_batch' % (start_audio, end_audio)
    h5_file = '/'.join((epoch_dir,session_name)) + '.h5'
    #h5_file = '/'.join((base_dir,"processed",epoch_dir,session_name)) + '.h5'
    
    (clusters, times, triggers, waveforms) = caton_utils.extract_info_from_h5(h5_file)
    
    grouped_stim_times = mw_utils.extract_and_group_stimuli(config.get('mworks','file'))
    
    # aggregated_stim_times = mw_utils.aggregate_stimuli(grouped_stim_times)
    
    spike_trains_by_cluster = caton_utils.spikes_by_cluster(times, clusters)
    spike_trains_by_channel = caton_utils.spikes_by_channel(times, triggers)
    
    nclusters = len(spike_trains_by_cluster)
    nchannels = len(spike_trains_by_channel)
    nstim = len(grouped_stim_times.keys())
    stim_keys = grouped_stim_times.keys()
    
    clusters_figure_dir = '/'.join((epoch_dir, "figures", "clusters"))
    if not os.path.exists(clusters_figure_dir): os.makedirs(clusters_figure_dir)
    
    channels_figure_dir = '/'.join((epoch_dir, "figures", "channels"))
    if not os.path.exists(channels_figure_dir): os.makedirs(channels_figure_dir)
    
    plt.ioff()
    f = plt.figure()
    
    for stim in range(0, len(stim_keys)):
        stim_key = stim_keys[stim]
        
        if stim_key in ['pixel clock', 'background', 'BlankScreenGray']:
            continue
        #if not (stim_key == 'BlueSquare'):
        #    continue
        
        # plot by cluster
        for ch in range(0, len(spike_trains_by_cluster)):
            print("Plotting cl %d, stim %s" % (ch, stim_key))
            
            # plt.subplot( nclusters, nstim, ch *nstim + stim)
            
            ev_locked = mw_utils.event_lock_spikes( grouped_stim_times[stim_key], 
                                                    spike_trains_by_cluster[ch], 0.1, 0.5,
                                                    time_base )
            mw_utils.plot_rasters(ev_locked)
            plt.title("clu %d, stim %s" % (ch, stim_key))
            plt.savefig("%s/clu%d_stim%s.pdf" % (clusters_figure_dir, ch, stim_key))
            plt.hold(False)
            plt.clf()
        
        # plot by channel
        for ch in range(0, len(spike_trains_by_channel)):
            print("Plotting ch %d, stim %s" % (ch, stim_key))
            
            ev_locked = mw_utils.event_lock_spikes( grouped_stim_times[stim_key],
                                                    spike_trains_by_cluster[ch], 0.1, 0.5,
                                                    time_base )
            mw_utils.plot_rasters(ev_locked)
            plt.title("ch %d, stim %s" % (ch, stim_key))
            plt.savefig("%s/ch%d_stim%s.pdf" % (channels_figure_dir, ch, stim_key))
            plt.hold(False)
            plt.clf()


#  ============================
#  ============ OLD ===========
#  ============================
# 
# mwTimeOffset = 1358.6488178654547 # mw time at audio time 0
# epochTime_mw = (2075.8280759999998, 5771.5493690000003) # mw time of starting and ending event for recording epoch
# 
# 
# # convert epoch time to audio units
# epochTime_audio = (epochTime_mw[0] - mwTimeOffset, epochTime_mw[1] - mwTimeOffset)
# 
# # add buffer 10 min on front side
# epochTime_audio = (epochTime_audio[0] + 10 * 60, epochTime_audio[1])
# 
# # get spikes for epoch
# caton_cluster_data(baseDir, 1, time_range=epochTime_audio)
