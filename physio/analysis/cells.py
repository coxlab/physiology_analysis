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

# # ----------------- Old -------------------
# 
# # import pywaveclus
# 
# # make this a 'dumb' version for right now... all clusters on all channels = cell
# 
# parser = OptionParser(usage="usage: %prog [options] [input file]")
# parser.add_option("-v", "--verbose", dest = "verbose",
#                     help = "enable verbose reporting",
#                     default = False, action = "store_true")
# 
# (options, args) = parser.parse_args()
# if options.verbose:
#     logging.basicConfig(level=logging.DEBUG)
# 
# if len(args) != 1:
#     logging.error("Must provide an input file")
#     parser.print_usage()
#     raise ValueError("Must provide an input file")
# 
# inFilename = args[0]
# 
# nchannels = 32
# nclusters = 5 # skipping first cluster
# 
# cells = []
# logging.debug("Opening file: %s" % inFilename)
# inFile = tables.openFile(inFilename, 'a')
# 
# class description(tables.IsDescription):
#     chan = tables.Int8Col()
#     clu = tables.Int8Col()
# 
# # check if cell table exists, if so, delete it
# if 'Cells' in inFile.root._v_children.keys():
#     logging.debug("File contains /Cells table, removing table...")
#     inFile.removeNode('/Cells', recursive = True)
# 
# celltable = inFile.createTable('/', 'Cells', description)
# 
# logging.debug("Adding cells")
# for ch in xrange(1,nchannels+1):
#     for cl in xrange(1,nclusters+1):
#         celltable.row['chan'] = ch
#         celltable.row['clu'] = cl
#         celltable.row.append()
# 
# logging.debug("Cleaning up")
# inFile.flush()
# inFile.close()