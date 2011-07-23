#!/usr/bin/env python

import logging, os, shutil, sys, tempfile

# logging.basicConfig(level=logging.DEBUG)

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

def analyze_session(session, customcfgfile=None):
    
    # read in configuration file
    config = cfg.Config()
    config.read_user_config()
    config.read_session_config(session)
    config.set_session(session)
    if not customcfgfile is None:
        config.read(customcfg)
    
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
            if offset is None:
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
    dlf = logging.FileHandler('/'.join((config.get('session','output'),'%s.log' % session)))
    dlf.setLevel(logging.DEBUG)
    logging.root.addHandler(dlf)
    
    time_base_file = '/'.join((config.get('session','scratch'),'time_base'))
    if os.path.exists(time_base_file):
        logging.debug("Found existing time_base: %s" % time_base_file)
        time_base = pixel_clock.load_time_base(time_base_file)
    else:
        logging.debug("Reading pixel clock (from audio files)")
        tmp_dir = tempfile.mkdtemp(dir=config.get('filesystem','tmp'))
        (pc_data, fs) = pixel_clock.read_pixel_clock(session_dir, config.get('pixel clock','scratch'), tmp_dir)
        shutil.rmtree(tmp_dir) # clean up temporary directory
        
        logging.debug("Parsing pixel clock")
        (reconstructed_events, offset_latencies) = pixel_clock.parse_pixel_clock(pc_data, 0., config.getint('audio','samprate'), \
                                                        pc_y_pos_deg = config.getfloat('pixel clock','y'), \
                                                        pc_height_deg = config.getfloat('pixel clock','h'), \
                                                        screen_height_deg = config.getfloat('pixel clock','screenh'))
        logging.info("Pixel clock offset latencies: %s" % str(offset_latencies))
        
        pc_codes = [e.code for e in reconstructed_events]
        pc_times = [e.time for e in reconstructed_events]
        
        logging.debug("Reading pixel clock (from mworks file)")
        (mw_times, mw_codes) = pixel_clock.read_pixel_clock_from_mw(config.get('mworks','file'))
        
        logging.debug("Finding time matches")
        time_base = pixel_clock.time_match_mw_with_pc( pc_codes, pc_times, mw_codes, mw_times)
        
        # clean up after pixel clock
        del mw_times, mw_codes, reconstructed_events, pc_codes, pc_times, offset_latencies, pc_data, fs
        
        logging.debug("Saving time_base: %s" % time_base_file)
        pixel_clock.save_time_base(time_base, time_base_file)
    
    # ================= find stable recording epoch (using mwks file) ===============
    logging.debug("Loading epochs [mwtime]")
    epochs_mw = utils.read_mw_epochs(session_dir, time_base, config.get('epochs','timeunit'))
    
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
        logging.info("Attempting to determine epochs from mworks file: %s" % config.get('mworks','file'))
        cnc_dict = cnc_utils.read_cnc_from_mw(config.get('mworks','file'))
        epochs_mw = cnc_utils.find_stable_epochs_in_events(cnc_dict) # in mw_time
        # save epochs file
        utils.save_mw_epochs(session_dir,epochs_mw,time_base,'mworks')
    
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
        
        epoch_dir = '/'.join((config.get('session','scratch'), session_name))
        
        tmp_dir = '/'.join((epoch_dir,'tmp'))
        
        clusterdir = '/'.join((epoch_dir,'clusters'))
        
        h5_file = '/'.join((epoch_dir,session_name)) + '.h5'
        if not (os.path.exists(h5_file)):
            epoch_dir = caton_utils.caton_cluster_data(session_dir, config.get('session','scratch'), \
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
        
        # move results
        results_filename = '%s/%s_%d_to_%d.h5' % (config.get('session','output'), \
                                                    session, start_audio, end_audio)
        logging.debug("Constructing results file: %s" % results_filename)
        if os.path.exists(results_filename):
            logging.warning("Results file already exists, deleting: %s" % results_filename)
            os.remove(results_filename)
        
        logging.debug("Moving caton results file: %s" % h5_file)
        shutil.move(h5_file, results_filename)
        
        logging.debug("Opening results file for appending info")
        # combine results into single (spike) file
        results_file = h5_utils.H5ResultsFileSaver(results_filename)
        results_file.add_session_h5_file(config.get('mworks','file'))
        results_file.add_mw_epoch_times(start_mw, end_mw)
        results_file.add_timebase(time_base_file)
        results_file.add_session_gdata(session_dict)
        results_file.add_probe_gdata(probe_dict)
        results_file.add_pad_positions(pad_positions)
        results_file.add_git_commit_id(utils.get_git_commit_id())
        results_file.close()
        
        logging.debug("Done processing epoch: %s" % str(epoch))
    
    if config.getboolean('filesystem','cleanup'):
        shutil.rmtree(config.get('session','scratch'))
    
    logging.debug("Finished analyzing session %s" % session)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    session = 'K4_110523'
    
    if len(sys.argv) > 1:
        session = sys.argv[1]
    
    analyze_session(session)