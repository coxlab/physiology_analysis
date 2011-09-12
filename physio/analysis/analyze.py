#!/usr/bin/env python

import copy, glob, logging, os, shutil, sys, tempfile

# logging.basicConfig(level=logging.DEBUG)

import numpy as np
import pylab as plt

from .. import cfg
import cells
from .. import clock
import cluster
from .. import h5
from .. import notebook
from .. import utils

def check_results(session, customCfgFile = None):
    # check if results version agrees with the current version
    config = cfg.load(session, customCfgFile)
    rf = config.get('session','output') + '/' + session + '.h5'
    if os.path.exists(rf):
        # TODO check if version agrees
        return
    
    # ...then re-analyze data
    analyze(session, customCfgFile)

def analyze(session, customCfgFile = None):
    
    # setup configuration TODO consolidate?
    config = cfg.load(session, customCfgFile)
    if not os.path.exists(config.get('session','output')): os.makedirs(config.get('session','output'))
    logging.root.addHandler(logging.FileHandler('%s/physio.log' % config.get('session','output'), mode='w'))
    # config = cfg.Config()
    # config.read_user_config()
    # config.read_session_config(session)
    # config.set_session(session)
    # if not customCfgFile is None: config.read(customCfgFile)
    
    # determine epochs
    sessionDict, probeDict = notebook.lookup_notes(config)
    epochs_audio = notebook.parse_epochs_string(sessionDict['stableepochs'])
    if len(epochs_audio) == 0: utils.error("No epochs found")
    
    # process pixel clock
    matches, _ = clock.pixelclock.process_from_config(config) # [:,0] = audio, [:,1] = mworks
    if len(matches) == 0: utils.error("No pixel clock matches found")
    
    # process each epoch
    for epoch_audio in epochs_audio:
        logging.debug("Processing epoch: %s" % str(epoch_audio))
        # pyc
        logging.debug("clustering")
        stdout, stderr = cluster.cluster_from_config(config, epoch_audio)
        logging.debug("clustering stdout:\n%s" % stdout)
        logging.debug("clustering stderr:\n%s" % stderr)
        
        # collate
        logging.debug("collating")
        resultsFilename = config.get('session','output') + '/' + session + '.h5'
        channelFiles = glob.glob(config.get('session','output')+'/*/*.h5')
        h5.combine.combine(channelFiles, resultsFilename)
        
        # find cells
        logging.debug("finding cells")
        cells.find_cells(resultsFilename)
        
        # add events
        logging.debug("adding events")
        eventsFilename = config.get('session','dir') + '/' + session + '.h5'
        h5.events.add_events_file(eventsFilename, resultsFilename)
        #resultsFile.add_session_h5_file(config.get('mworks','file'))
        
        # add pixelclock
        logging.debug("adding pixel clock matches")
        offsetMatches = np.array(copy.deepcopy(matches))
        offsetMatches[:,0] = (offsetMatches[:,0] - epoch_audio[0]) / float(config.getint('audio','samprate'))
        h5.utils.write_array(resultsFilename, offsetMatches, 'TimeMatches', 'PC - MW Time Matches')
        
        # add session info
        logging.debug("adding sesison information")
        h5.utils.write_epoch_audio(resultsFilename, epoch_audio)
        h5.utils.write_dict(resultsFilename, sessionDict, 'SessionGData', 'Session data from GDocs')
        h5.utils.write_dict(resultsFilename, probeDict, 'ProbeGData', 'Probe data from GDocs')
        # results_file.add_pad_positions(pad_positions)
        h5.utils.write_git_commit_id(resultsFilename, utils.get_git_commit_id())
    
    # TODO fix this to equalize disk usage:
    #  read from one -> write to other -> cleanup by copying files back over
    # if config.getboolean('filesystem','cleanup'):
    #     shutil.rmtree(config.get('session','scratch'))
    
    logging.debug("Finished analyzing session %s" % session)
