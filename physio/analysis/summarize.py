#!/usr/bin/env python

import logging

import pylab as pl

import tables

from .. import spikes

def summarize(session, outputFilename, binsize=0.05, binwindow=(-200,700)):
    """
    Generate a summary/intermediate representation that contains
    1) trial times
    2) per-trial stimulus description
    3) spikes binned and locked to individual trials
    """
    trialTimes, stimuli, _, _ = session.get_trials()
    targetTimes, blueStimuli = session.get_stimuli(stimType = 'rectangle')
    allStimTimes = trialTimes + targetTimes
    allStimuli = stimuli + blueStimuli
    
    # table format:
    # <trial_time> <channel> <cluster> <stim_id> <stim_x> <stim_y> <stim_size> <bins...>
    #  where bins are:
    tbins = pl.arange(binwindow[0],binwindow[1]+binsize/2,binsize)
    tbins = zip(tbins[:-1],tbins[1:])
    
    class TrialSpikes(tables.IsDescription):
        time = tables.Float64Col()
        channel = tables.UInt8Col()
        cluster = tables.UInt8Col()
        stimID = tables.StringCol(16)
        stimX = tables.Float32Col()
        stimY = tables.Float32Col()
        stimSize = tables.Float32Col()
        bins = tables.UInt16Col(len(tbins))
    
    # make output file
    outputFile = tables.openFile(outputFilename, 'w')
    trialTable = outputFile.createTable('/', 'Trials', TrialSpikes)
    for cellI in xrange(session.get_n_cells()):
        logging.debug("Processing cell: %i" % cellI)
        ch, cl = session.get_cell(cellI)
        spikeTimes = session.get_spike_times(ch, cl)
        spikeBins = pl.zeros((len(allStimTimes),len(tbins)))
        for (i,tbin) in enumerate(tbins):
            spikeBins[:,i] = pl.array([len(bs) for bs in spikes.stats.event_lock(allStimTimes, spikeTimes, tbin[0], tbin[1])])
        # write data for this cell
        for (tt, st, tb) in zip(allStimTimes, allStimuli, spikeTimes):
                trialTable.row['time'] = tt
                trialTable.row['channel'] = ch
                trialTable.row['cluster'] = cl
                trialTable.row['stimID'] = st['name']
                trialTable.row['stimX'] = st['pos_x']
                trialTable.row['stimY'] = st['pos_y']
                trialTable.row['stimSize'] = st['size_x']
                trialTable.row['bins'] = tb
                trialTable.row.append()
        outputFile.flush()
    
    # TODO add hash of session hdf5 file

    outputFile.flush()
    outputFile.close()
