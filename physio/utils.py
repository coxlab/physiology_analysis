#!/usr/bin/env python

import logging, os

import numpy as np

def read_epochs(data_directory):
    """
    Read in manually defined epoch time-ranges [in audio time units]
    """
    epochs = []
    epochFilename = '/'.join((data_directory,"epochs"))
    if not (os.path.exists(epochFilename)):
        logging.info("No epoch file found: %s" % epochFilename))
        return epochs # epochFilename did not exist, so return the blank list
    else:
        # try to load the custom epoch file
        epochs = np.loadtxt(epochFilename)
        if epochs.shape[1] != 2:
            raise IOError("Epoch file shape incorrect: %s" % epochFilename) # epoch file was not shaped correctly
        return epochs