#!/usr/bin/env python

import logging, os, shutil, sys, tempfile

logging.basicConfig(level=logging.DEBUG)

import numpy as np
import pylab as plt

import caton_utils
import cfg
import cnc_utils
import h5_utils
import mw_utils
import notebook
import pixel_clock
import utils
# from caton_utils import caton_cluster_data, extract_info_from_h5
# from pixel_clock import read_pixel_clock, parse_pixel_clock, read_pixel_clock_from_mw, time_match_mw_with_pc
# from cnc_utils import read_cnc_from_mw, find_stable_epochs_in_events

session = 'K4_110523'
if len(sys.argv) > 1:
    session = sys.argv[1]

# read in configuration file
config = cfg.Config()
config.read_user_config()
config.read_session_config(session)
config.set_session(session)

session_dict = notebook.lookup_session(config)
if not (session_dict is None):
    if config.get('probe','id').strip() == '': # probe is not defined
        logging.debug("Using probe from notebook: %s" % session_dict['electrode'])
        if session_dict['electrode'].strip() == '':
            logging.error("No probe found in notebook entry")
            raise ValueError("No probe found in notebook entry")
        config.set('probe','id',session_dict['electrode'].lower().strip())
else:
    logging.warning("Failed to fetch session information from notebook entry")

probe_dict = notebook.lookup_probe(config)
if config.get('probe','offset').strip() == '': # offset is not defined
    if not (probe_dict is None):
        offset = notebook.offset_to_float(probe_dict['offset'])
        logging.debug("Using probe offset from notebook: %s" % str(offset))
        if offset is None
            logging.error("No probe offset in notebook entry")
            raise ValueError("No probe offset in notebook entry")
        config.set('probe','offset',str(offset))
    else:
        logging.error("Failed to fetch probe information from electrode inventory")
        raise ValueError("Failed to fetch probe information from electrode inventory")
if probe_dict is None:
    logging.error("Failed to fetch probe information from electrode inventory")
    raise ValueError("Failed to fetch probe information from electrode inventory")

session_dir = config.get('session','dir')

# make necessary output directories
utils.make_output_dirs(config)

# setup logging
dlf = logging.FileHandler('/'.join((config.get('session','output'),'debug.log')))
dlf.setLevel(logging.DEBUG)
logging.root.addHandler(dlf)

# data_repo = '/Volumes/Scratch'
# session = 'K4_110523'
# base_dir = '/'.join((data_repo, session))
# # base_dir =  '/Volumes/Scratch/K4_110523'
# cache_dir = "/Volumes/Scratch/tmp/"
# mw_filename = '/'.join((base_dir, session)) + '.mwk'
# 
# if not (os.path.exists(cache_dir)): os.makedirs(cache_dir)

# ==================== match pixel clock (on whole dataset) =====================
# def load_time_base(time_base_file):
#     f = open(time_base_file,'rb')
#     evt_zipper, audio_offset = pickle.load(f)
#     f.close()
#     return pixel_clock.TimeBase(evt_zipper, audio_offset)
# 
# def save_time_base(time_base, time_base_file):
#     f = open(time_base_file,'wb')
#     pickle.dump((time_base.evt_zipper, time_base.audio_offset), f, 2)
#     f.close()

time_base_file = '/'.join((config.get('session','output'),'time_base'))
if os.path.exists(time_base_file):
    logging.debug("Found existing time_base: %s" % time_base_file)
    time_base = pixel_clock.load_time_base(time_base_file)
else:
    # read_pixel_clock( project_path, file_no, cache_dir="/tmp", time_range=None): return (pc_data, fs)
    # (pc_data, fs) = pixel_clock.read_pixel_clock( base_dir, 1 , cache_dir )
    logging.debug("Reading pixel clock (from audio files)")
    tmp_dir = tempfile.mkdtemp(dir=config.get('filesystem','tmp'))
    (pc_data, fs) = pixel_clock.read_pixel_clock(session_dir, config.get('pixel clock','output'), tmp_dir)
    shutil.rmtree(tmp_dir) # clean up temporary directory
    
    # parse_pixel_clock(pc_data, start_time_sec, samples_per_sec,
    #                       arm_threshold = 0.1, arm_timeout = 0.005, 
    #                       accept_threshold = 0.3, derivative_threshold = 0.0,
    #                       time_stride=0.0005, refractory_period = 0.010,
    #                       event_trigger_period = 0.05,
    #                       pc_y_pos_deg = None,
    #                       pc_height_deg = None,
    #                       screen_height_deg = None): return reconstructed_events, offset_latencies
    # TODO : read pc_y_pos_deg and pc_height_deg from mworks file
    logging.debug("Parsing pixel clock")
    (reconstructed_events, offset_latencies) = pixel_clock.parse_pixel_clock(pc_data, 0., config.getint('audio','samprate'), \
                                                    pc_y_pos_deg = config.getfloat('pixel clock','y'), \
                                                    pc_height_deg = config.getfloat('pixel clock','h'), \
                                                    screen_height_deg = config.getfloat('pixel clock','screenh'))
    logging.info("Pixel clock offset latencies: %s" % str(offset_latencies))
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
    logging.debug("Reading pixel clock (from mworks file)")
    (mw_times, mw_codes) = pixel_clock.read_pixel_clock_from_mw(config.get('mworks','file'))

    # time_match_mw_with_pc(pc_codes, pc_times, mw_codes, mw_times,
    #                                 submatch_size = 10, slack = 0, max_slack=10,
    #                                 pc_check_stride = 100, pc_file_offset= 0): return TimeBase(time_matches, pc_file_offset)
    logging.debug("Finding time matches")
    time_base = pixel_clock.time_match_mw_with_pc( pc_codes, pc_times, mw_codes, mw_times)

    # clean up after pixel clock
    del mw_times, mw_codes, reconstructed_events, pc_codes, pc_times, offset_latencies, pc_data, fs
    
    logging.debug("Saving time_base: %s" % time_base_file)
    pixel_clock.save_time_base(time_base, time_base_file)


# ================= find stable recording epoch (using mwks file) ===============
logging.debug("Loading epochs [mwtime]")
epochs_mw = utils.read_mw_epochs(session_dir, time_base, config.get('epochs','timeunit'))

# if config.get('epochs','timeunit') == 'mworks':
#     epochs = utils.read_epochs_mw(session_dir, time_base)
#     logging.debug("Loaded mworks epochs: %s" % str(epochs))
# elif config.get('epochs','timeunit') == 'audio':
#     epochs = utils.read_epochs_audio(session_dir)
#     logging.debug("Loaded audio epochs: %s" % str(epochs))
# else:
#     logging.error("epochs timeunit: %s not valid" % config.get('epochs','timeunit'))

if len(epochs_mw) == 0: # if epochs are undefined try to read from gdata
    if not (session_dict is None):
        logging.info("Attempting to read epochs from gdata session info")
        try:
            epochs_audio = np.array(notebook.parse_epochs_string(session_dict['stableepochs']))
            # convert to mworks times
            ufunc_audio_to_mw = np.frompyfunc(time_base.audio_time_to_mw, 1, 1)
            epochs_mw = ufunc_audio_to_mw(epochs_audio)
        except Exception as e:
            logging.warning("Failed to parse epoch string:%s [%s]" % (session_dict['stableepochs'], str(e)))
            epochs_mw = []
        if len(epochs_mw) != 0:
            logging.info("Epochs parsed from notebook session info")
            logging.info("Epochs mworks: %s" % str(epochs_mw))
            logging.info("Epochs audio : %s" % str(epochs_audio))
            utils.save_mw_epochs(session_dir,epochs_mw,time_base,'mworks')

if len(epochs_mw) == 0: # if epochs are still undefined, try to read from mworks file
    logging.info("Attempting to determine epochs from mworks file: %s" % config.get('session','output'))
    cnc_dict = cnc_utils.read_cnc_from_mw(config.get('mworks','file'))
    epochs_mw = cnc_utils.find_stable_epochs_in_events(cnc_dict) # in mw_time
    # save epochs file
    utils.save_mw_epochs(session_dir,epochs_mw,time_base,'mworks')

# def find_epoch_dir(output_dir, session_name, index = 0):
#     epoch_dir = '/'.join((output_dir, session_name))
#     if index == 0:
#         epoch_dir += '_%i' % index
#     if not (os.path.exists(epoch_dir)):
#         return epoch_dir
#     else:
#         return find_epoch_dir(output_dir, session_name, index+1)

# ================================ cluster epoch ================================
for epoch in epochs_mw:
    start_mw, end_mw = epoch
    start_mw += config.getfloat('epochs','settletime')
    #start_mw += 60 * 5 # give time for electrode to settle
    logging.debug("Processing epoch [mw time]: %.2f %.2f" % (start_mw, end_mw))
    time_base.audio_offset = 0.
    start_audio = time_base.mw_time_to_audio(start_mw)
    end_audio = time_base.mw_time_to_audio(end_mw)
    time_base.audio_offset = -start_audio
    
    # cluster epoch
    session_name = 'session_%d_to_%d_a32_batch' % (start_audio, end_audio)
    
    # epoch_dir = find_epoch_dir(config.get('session','output'), session_name)
    epoch_dir = '/'.join((config.get('session','output'), session_name))
    
    # tmp_dir = '/'.join((config.get('session','output'),'tmp',session_name))
    tmp_dir = '/'.join((epoch_dir,'tmp'))
    
    # epoch_dir = '/'.join((config.get('session','output'),session_name))
    clusterdir = '/'.join((epoch_dir,'clusters'))
    # if not (os.path.exists(clusterdir)):
    #     os.makedirs(clusterdir)
    
    h5_file = '/'.join((epoch_dir,session_name)) + '.h5'
    # if not (os.path.exists(h5_file)):
    epoch_dir = caton_utils.caton_cluster_data(session_dir, config.get('session','output'), \
                            clusterdir, time_range=(start_audio, end_audio), tmp_dir=tmp_dir)
    
    # get electrode/pad positions
    pad_positions_file = '/'.join((epoch_dir,'pad_positions'))
    if os.path.exists(pad_positions_file):
        pad_positions = np.loadtxt(pad_positions_file)
    else:
        cncDict = cnc_utils.read_cnc_from_mw(config.get('mworks','file'))
        tipOffset = config.getfloat('probe','offset')
        pad_positions = cnc_utils.find_channel_positions(cncDict, epoch, tipOffset)
        np.savetxt(pad_positions_file,pad_positions)
    
    # combine results into single (spike) file
    results_file = h5_utils.H5ResultsFileSaver(h5_file)
    results_file.add_session_h5_file(config.get('mworks','file')):
    results_file.add_mw_epoch_times(start_mw, end_mw):
    results_file.add_timebase(time_base_file):
    results_file.add_session_gdata(session_dict):
    results_file.add_probe_gdata(probe_dict):
    results_file.add_pad_positions(pad_positions):
    results_file.add_git_commit_id(utils.get_git_commit_id()):
    results_file.close():
    
    # # ======================= generate plots for epoch ==========================
    #     # TODO this data<->filename association is too opaque
    #     
    #     h5_file = '/'.join((epoch_dir,session_name)) + '.h5'
    #     #h5_file = '/'.join((base_dir,"processed",epoch_dir,session_name)) + '.h5'
    #     
    #     (clusters, times, triggers, waveforms) = caton_utils.extract_info_from_h5(h5_file)
    #     
    #     grouped_stim_times = mw_utils.extract_and_group_stimuli(config.get('mworks','file'))
    #     
    #     # aggregated_stim_times = mw_utils.aggregate_stimuli(grouped_stim_times)
    #     
    #     spike_trains_by_cluster = caton_utils.spikes_by_cluster(times, clusters)
    #     spike_trains_by_channel = caton_utils.spikes_by_channel(times, triggers)
    #     
    #     nclusters = len(spike_trains_by_cluster)
    #     nchannels = len(spike_trains_by_channel)
    #     nstim = len(grouped_stim_times.keys())
    #     stim_keys = grouped_stim_times.keys()
    #     
    #     clusters_figure_dir = '/'.join((epoch_dir, "figures", "clusters"))
    #     if not os.path.exists(clusters_figure_dir): os.makedirs(clusters_figure_dir)
    #     
    #     channels_figure_dir = '/'.join((epoch_dir, "figures", "channels"))
    #     if not os.path.exists(channels_figure_dir): os.makedirs(channels_figure_dir)
    #     
    #     plt.ioff()
    #     f = plt.figure()
    #     
    #     for stim in range(0, len(stim_keys)):
    #         stim_key = stim_keys[stim]
    #         
    #         if stim_key in ['pixel clock', 'background', 'BlankScreenGray']:
    #             continue
    #         #if not (stim_key == 'BlueSquare'):
    #         #    continue
    #         
    #         # plot by cluster
    #         for ch in range(0, len(spike_trains_by_cluster)):
    #             print("Plotting cl %d, stim %s" % (ch, stim_key))
    #             
    #             # plt.subplot( nclusters, nstim, ch *nstim + stim)
    #             
    #             ev_locked = mw_utils.event_lock_spikes( grouped_stim_times[stim_key], 
    #                                                     spike_trains_by_cluster[ch], 0.1, 0.5,
    #                                                     time_base )
    #             mw_utils.plot_rasters(ev_locked)
    #             plt.title("clu %d, stim %s" % (ch, stim_key))
    #             plt.savefig("%s/clu%d_stim%s.pdf" % (clusters_figure_dir, ch, stim_key))
    #             plt.hold(False)
    #             plt.clf()
    #         
    #         # plot by channel
    #         for ch in range(0, len(spike_trains_by_channel)):
    #             print("Plotting ch %d, stim %s" % (ch, stim_key))
    #             
    #             ev_locked = mw_utils.event_lock_spikes( grouped_stim_times[stim_key],
    #                                                     spike_trains_by_channel[ch], 0.1, 0.5,
    #                                                     time_base )
    #             mw_utils.plot_rasters(ev_locked)
    #             plt.title("ch %d, stim %s" % (ch, stim_key))
    #             plt.savefig("%s/ch%d_stim%s.pdf" % (channels_figure_dir, ch, stim_key))
    #             plt.hold(False)
    #             plt.clf()


logging.debug("FINISHED")
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
