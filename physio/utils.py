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