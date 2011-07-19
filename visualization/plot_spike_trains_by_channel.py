#!/usr/bin/env python

import logging, os
logging.basicConfig(level=logging.DEBUG)

import matplotlib
matplotlib.use('MacOSX') # doesn't like QT?

import numpy as np
import pylab as plt

# add path of physio module
import sys
sys.path.append('../')

import physio

session = 'K4_110715'
if len(sys.argv) > 1:
    session = sys.argv[1]

# read in configuration file
config = physio.cfg.Config()
config.read_user_config()
config.read_session_config(session)
config.set_session(session)

# load time_base
time_base_file = '/'.join((config.get('session','output'),'time_base'))
if os.path.exists(time_base_file):
    logging.debug("Found existing time_base: %s" % time_base_file)
    time_base = physio.pixel_clock.load_time_base(time_base_file)
else:
    raise IOError("Time base does not exist: %s" % time_base_file)

# get sessions
sessions = physio.utils.get_sessions(config.get('session','output'))
logging.debug("Found sessions: %s" % str(sessions))

# load epochs
epochs_mw = physio.utils.read_mw_epochs(config.get('session','dir'), time_base, config.get('epochs','timeunit'))
if len(epochs_mw) != len(sessions):
    raise ValueError("len(epochs)[%i] != len(sessions)[%i]" % (len(epochs_mw), len(sessions)))

# plot each session
for epoch_mw, session in zip(epochs_mw, sessions):
    
    # fixing ugly time_base
    start_mw, end_mw = epoch_mw
    start_mw += config.getfloat('epochs','settletime')
    time_base.audio_offset = 0.
    start_audio = time_base.mw_time_to_audio(start_mw)
    end_audio = time_base.mw_time_to_audio(end_mw)
    time_base.audio_offset = -start_audio
    
    session_name = os.path.basename(session)#'session_%d_to_%d_a32_batch' % (start_audio, end_audio)
    epoch_dir = '/'.join((config.get('session','output'), session_name))
    h5_file = '/'.join((epoch_dir,session_name)) + '.h5'
    (clusters, times, triggers, waveforms) = physio.caton_utils.extract_info_from_h5(h5_file)
    
    grouped_stim_times = physio.mw_utils.extract_and_group_stimuli(config.get('mworks','file'))
    spike_trains_by_channel = physio.caton_utils.spikes_by_channel(times, triggers)
    
    channels_figure_dir = '/'.join((epoch_dir, "figures", "channels"))
    if not os.path.exists(channels_figure_dir): os.makedirs(channels_figure_dir)
    
    stim_keys = grouped_stim_times.keys()
    for stim in range(0, len(stim_keys)):
        stim_key = stim_keys[stim]
    
        if stim_key in ['pixel clock', 'background', 'BlankScreenGray']:
            continue
        for ch in range(0, len(spike_trains_by_channel)):
            print("Plotting ch %d, stim %s" % (ch, stim_key))
        
            ev_locked = physio.mw_utils.event_lock_spikes( grouped_stim_times[stim_key],
                                                    spike_trains_by_channel[ch], 0.1, 0.5,
                                                    time_base )
            physio.mw_utils.plot_rasters(ev_locked)
            plt.title("ch %d, stim %s" % (ch, stim_key))
            plt.savefig("%s/ch%d_stim%s.pdf" % (channels_figure_dir, ch, stim_key))
            plt.hold(False)
            plt.clf()