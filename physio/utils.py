#!/usr/bin/env python

import logging, os

import numpy as np

def read_epochs_audio(data_directory):
    """
    Read in manually defined epoch time-ranges [in audio time units]
    """
    epochs = []
    epochFilename = '/'.join((data_directory,"epochs"))
    if not (os.path.exists(epochFilename)):
        logging.info("No epoch file found: %s" % epochFilename)
        return epochs # epochFilename did not exist, so return the blank list
    else:
        # try to load the custom epoch file
        epochs = np.loadtxt(epochFilename)
        if epochs.shape[1] != 2:
            raise IOError("Epoch file shape incorrect: %s" % epochFilename) # epoch file was not shaped correctly
        return epochs

def read_epochs_mw(data_directory, time_base):
    """
    Read in manually defined epoch time-ranges [in mw time units]
    
    this requires a time_base object that can map audio times to mworks times
    """
    audio_epochs = read_epochs_audio(data_directory)
    ufunc_audio_to_mw = np.frompyfunc(time_base.audio_time_to_mw, 1, 1)
    return ufunc_audio_to_mw(audio_epochs)

def make_output_dirs(config):
    tmp = config.get('filesystem','tmp')
    if not (os.path.exists(tmp)): os.makedirs(tmp)
    
    output_dir = config.get('session','output')
    if not (os.path.exists(output_dir)): os.makedirs(output_dir)
    
    pixel_clock_output = config.get('pixel clock','output')
    if not (os.path.exists(pixel_clock_output)): os.makedirs(pixel_clock_output)
