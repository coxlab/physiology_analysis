#!/usr/bin/env python

import copy, logging, os
logging.basicConfig(level=logging.DEBUG)

import matplotlib
matplotlib.use('qt4Agg') # doesn't like QT?

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

# get stimulus times
logging.debug("Reading stimulus information")
stimtimer = physio.stimsorter.StimTimer()
stimtimer.blacklist += ['BlueSquare',]
mwkf = physio.mw_utils.make_reader(config.get('mworks','file'))
mwkf.open()
events = mwkf.get_events(codes=['#announceStimulus'])
[stimtimer.process_mw_event(e) for e in events]
mwkf.close()

def unique(inList):
    d = {}
    for i in inList:
        d[i] = 1
    return d.keys()

stim_names = [str(n) for n in sorted(unique([s.intName for s in stimtimer.stimList]))]
pos_xs = sorted(unique([s.pos_x for s in stimtimer.stimList]))
pos_ys = sorted(unique([s.pos_y for s in stimtimer.stimList]))
size_xs = sorted(unique([s.size_x for s in stimtimer.stimList]))

for (l,s) in zip([stim_names,pos_xs,pos_ys,size_xs],['names','pos_x','pos_y','size_x']):
    logging.debug("Found %i %s" % (len(l),s))

#subplots_width = len(pos_xs) + len(pos_ys) - 1 + len(size_xs)
subplots_height = len(stim_names)


valid_stims = []
for s in size_xs:
    for y in pos_ys:
        for x in pos_xs:
            for name in stim_names:
                stim = physio.stimsorter.Stim({'name':name,
                            'pos_x': x, 'pos_y': y,
                            'size_x': s, 'size_y': s,
                            'rotation': 0})
                if stimtimer.find_stim(stim) != -1:
                    stim.name = '' # set name to blank for name free matching later
                    valid_stims.append(stim)
                    break

subplots_width = len(valid_stims)
logging.debug("subplots w:%i, h:%i" % (subplots_width, subplots_height))

#grouped_stim_times = physio.mw_utils.extract_and_group_stimuli(config.get('mworks','file'))

# plot each session
for epoch_mw, session in zip(epochs_mw, sessions):
    
    # fixing ugly time_base
    start_mw, end_mw = epoch_mw
    start_mw += config.getfloat('epochs','settletime')
    # I think was done to calulate the audio start time with no offset (considering the whole recording session)
    time_base.audio_offset = 0.
    start_audio = time_base.mw_time_to_audio(start_mw)
    end_audio = time_base.mw_time_to_audio(end_mw)
    # now setup the time_base to give times relative to the stable epoch (not the start of the session)
    time_base.audio_offset = -start_audio
    
    session_name = os.path.basename(session)#'session_%d_to_%d_a32_batch' % (start_audio, end_audio)
    epoch_dir = '/'.join((config.get('session','output'), session_name))
    h5_file = '/'.join((epoch_dir,session_name)) + '.h5'
    (clusters, times, triggers, waveforms) = physio.caton_utils.extract_info_from_h5(h5_file)
    
    spike_trains_by_channel = physio.caton_utils.spikes_by_channel(times, triggers)
    
    psths_figure_dir = '/'.join((epoch_dir, "figures", "psths"))
    if not os.path.exists(psths_figure_dir): os.makedirs(psths_figure_dir)
    
    for ch in range(0, len(spike_trains_by_channel)):
        logging.info("Plotting ch %d" % ch)
        # setup figure
        plt.figure(figsize=(subplots_width, subplots_height))
        plt.gcf().suptitle('Channel %d' % ch)
        plt.subplot(subplots_height, subplots_width,1)
        
        for (subplots_y, sn) in enumerate(stim_names):
            for (subplots_x, vs) in enumerate(valid_stims):
                stim = copy.deepcopy(vs)
                stim.name = sn
                
                stimI = stimtimer.find_stim(stim)
                if stimI == -1:
                    raise ValueError("stimulus: %s was not found when plotting" % stim)
                stim_times = stimtimer.times[stimI]
                
                ev_locked = physio.mw_utils.event_lock_spikes( stim_times,
                                                    spike_trains_by_channel[ch], 0.1, 0.5,
                                                    time_base )
                subplots_i = subplots_x + subplots_y * subplots_width + 1
                plt.subplot(subplots_height, subplots_width, subplots_i)
                physio.mw_utils.plot_rasters(ev_locked)
                a = plt.gca()
                a.set_yticks([])
                a.set_yticklabels([])
                xm = a.get_xlim()[0] + (a.get_xlim()[1] - a.get_xlim()[0]) / 2.
                ym = a.get_ylim()[0] + (a.get_ylim()[1] - a.get_ylim()[0]) / 2.
                a.text(xm,ym,'%i' % int(a.get_ylim()[1]), color='r', zorder=-1000,
                    horizontalalignment='center', verticalalignment='center')
                # a.set_yticks([a.get_ylim()[1]])
                # a.set_yticklabels([str(a.get_ylim()[1])],
                #     horizontalalignment='left', color='r', alpha=0.8)
                if subplots_x == 0:
                    a.set_ylabel(stim.name, rotation='horizontal',
                        horizontalalignment='right', verticalalignment='center')
                if subplots_y != (len(stim_names) - 1):
                    a.set_xticks([])
                    a.set_xticklabels([])
                else:
                    a.set_xticks([0.,0.5])
                    a.set_xticklabels(['0','0.5'])
                if subplots_y == 0:
                    a.set_title('%i,%i[%i]' % (stim.pos_x, stim.pos_y, stim.size_x),
                        rotation=45, horizontalalignment='left', verticalalignment='bottom')
        # plt.show()
        plt.savefig("%s/ch%d_psth.pdf" % (psths_figure_dir, ch))
        plt.hold(False)
        plt.clf()