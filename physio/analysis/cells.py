#!/usr/bin/env python

import logging
from optparse import OptionParser

import tables

def find_cells(resultsFilename, nchannels = 32, nclusters = 5):
    cells = []
    logging.debug("Adding cells to: %s" % resultsFilename)
    resultsFile = tables.openFile(resultsFilename, 'a')
    
    class description(tables.IsDescription):
        chan = tables.Int8Col()
        clu = tables.Int8Col()
    
    # check if cell table exists, if so, delete it
    if '/Cells' in resultsFile:
        logging.debug("Removing existing /Cells from %s" % filename)
        resultsFile.removeNode('/Cells', recursive = True)
    
    cellTable = resultsFile.createTable('/', 'Cells', description)
    
    for ch in xrange(1,nchannels+1):
        for cl in xrange(1,nclusters+1):
            cellTable.row['chan'] = ch
            cellTable.row['clu'] = cl
            cellTable.row.append()
    
    resultsFile.flush()
    resultsFile.close()