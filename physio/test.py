#!/usr/bin/env python

import sys

from caton_utils import caton_cluster_data
from pixel_clock import read_pixel_clock, parse_pixel_clock, read_pixel_clock_from_mw, time_match_mw_with_pc
from cnc_utils import read_cnc_from_mw, find_stable_epochs_in_events

data_repo = '/Volumes/Scratch'
session = 'K4_11053'
base_dir = '/'.join((data_repo, session))
# base_dir =  '/Volumes/Scratch/K4_110523'
cache_dir = "/Volumes/Scratch/tmp/"
mw_filename = '/'.join((base_dir, session)) + '.mwk'

# ==================== match pixel clock (on whole dataset) =====================

# read_pixel_clock( project_path, file_no, cache_dir="/tmp", time_range=None): return (pc_data, fs)
(pc_data, fs) = read_pixel_clock( base_dir, 1 , cache_dir )

# parse_pixel_clock(pc_data, start_time_sec, samples_per_sec,
#                       arm_threshold = 0.1, arm_timeout = 0.005, 
#                       accept_threshold = 0.3, derivative_threshold = 0.0,
#                       time_stride=0.0005, refractory_period = 0.010,
#                       event_trigger_period = 0.05,
#                       pc_y_pos_deg = None,
#                       pc_height_deg = None,
#                       screen_height_deg = None): return reconstructed_events, offset_latencies
# TODO : read pc_y_pos_deg and pc_height_deg from mworks file
pc_y_pos_deg = -28
pc_height_deg = 2.5 # TODO check this
screen_height_deg = 137.214 # TODO can I read this from mworks?
(reconstructed_events, offset_latencies) = parse_pixel_clock(pc_data, 0., 44100, \
                                                            pc_y_pos_deg = pc_y_pos_deg,\
                                                            pc_height_deg = ,\
                                                            screen_height_deg = screen_height_deg)
pc_codes = [e[2] for e in reconstructed_events]
pc_times = [e[0] for e in reconstructed_events]

# read_pixel_clock_from_mw(mw_filename, use_display_update=True): return (float_times, codes)
(mw_times, mw_codes) = read_pixel_clock_from_mw(mw_filename)

# time_match_mw_with_pc(pc_codes, pc_times, mw_codes, mw_times,
#                                 submatch_size = 10, slack = 0, max_slack=10,
#                                 pc_check_stride = 100, pc_file_offset= 0): return TimeBase(time_matches, pc_file_offset)
time_base = time_match_mw_with_pc( pc_codes, pc_times, mw_codes, mw_times)


# ================= find stable recording epoch (using mwks file) ===============
cnc_dict = read_cnc_from_mw(mw_filename)
epochs = find_stable_epochs_in_events(cnc_dict) # in mw_time

# ================================ cluster epoch ================================
for epoch in epochs:
    start_mw, end_mw = epoch
    start_mw += 60 * 5 # give time for electrode to settle
    start_audio = time_base.mw_time_to_audio(start_mw)
    end_audio = time_base.mw_time_to_audio(end_mw)
    
    # cluster epoch
    caton_cluster(base_dir, 1, time_range=(start_audio, end_audio))
    
    # TODO save time_base and start/end times


# =========================== generate plots for epoch ==========================


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