#!/usr/bin/env python

import glob, logging, os, re, sys
from optparse import OptionParser

import numpy as np
import tables

import utils # h5 utils

def find_channel(filepath, regex):
    """
    Parameters
    ----------
    filepath : string
        Name of audio file (either full, relative, or basename).
    regex : string
        Regex with 1 group to find channel number from filename
    
    Returns
    -------
    channel : int
        Channel index of the audio file
    """
    m = re.match(regex, os.path.basename(filepath))
    if m is None:
        raise ValueError("No channel found for %s" % filepath)
    g = m.groups()
    if len(g) != 1:
        raise ValueError("Too many channels found for %s : %s" % (filepath, str(g)))
    try:
        return int(g[0])
    except:
        raise ValueError("Invalid (non-int) channel found for %s : %s" % (filepath, g[0]))

def combine(inputFiles, outputFilename, channelRegex = r'[a-z,A-Z]+_([0-9]+)\#*'):
    """
    Parameters
    ----------
    inputFiles : list of strings
    outputFilename :
    channelRegex :
    """
    assert np.iterable(inputFiles), "inputFiles[%s] must be iterable" % str(inputFiles)
    
    # get channels
    channels = [find_channel(f, channelRegex) for f in inputFiles]
    
    # make outputfile
    outputFile = tables.openFile(outputFilename, 'w')
    
    # setup output file
    logging.debug("creating output file groups")
    channelsgroup = outputFile.createGroup('/', 'Channels', 'SPC results')
    spcgroup = outputFile.createGroup('/', 'SPC', 'SPC results')
    outputFile.flush()
    
    # add each input file
    logging.debug("processing input files")
    for (ch, f) in zip(channels, inputFiles):
        logging.debug("opening: %s" % f)
        infile = tables.openFile(f,'r')
        
        logging.debug("copying spike table")
        # SpikeTable/<wave/time/clu>
        stdescription = infile.root.SpikeTable.description
        spiketable = outputFile.createTable(channelsgroup, 'ch%i' % ch, stdescription)
        for r in infile.root.SpikeTable:
            for k in stdescription._v_colObjects.keys():
                spiketable.row[k] =  r[k]
            spiketable.row.append()
        outputFile.flush()
        
        logging.debug("copying spc results")
        # SPC/<cdata/ctree>
        spcg = outputFile.createGroup(spcgroup, 'ch%i' % ch, 'Channel %i SPC results' % ch)
        if '/SPC/cdata' in infile and '/SPC/ctree' in infile:
            infile.createArray(spcg, 'cdata', np.array(infile.root.SPC.cdata))
            infile.createArray(spcg, 'ctree', np.array(infile.root.SPC.ctree))
        outputFile.flush()
        
        # meta data
        logging.debug("adding metadata")
        # original file
        spiketable.attrs.ORIGFILE = f
        logging.debug("closing: %s" % f)
        infile.close()
    
    # close output file
    logging.debug("closing: %s" % outputFilename)
    outputFile.flush()
    outputFile.close()
