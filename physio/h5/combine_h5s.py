#!/usr/bin/env python

import glob, logging, os, re, sys
from optparse import OptionParser

import numpy as np
import tables

parser = OptionParser(usage="usage: %prog [options] [input_h5_files...] [output_h5_file]")
parser.add_option("-r", "--regex", dest = "regex",
                    help = "regex (containing 1 group) to find channel from filename",
                    default = r'[a-z,A-Z]+_([0-9]+)\#*')
parser.add_option("-v", "--verbose", dest = "verbose",
                    help = "enable verbose reporting",
                    default = False, action = "store_true")

(options, args) = parser.parse_args()
if options.verbose:
    logging.basicConfig(level=logging.DEBUG)

# parse args
assert len(args) > 1, ValueError("Must supply at least 2 arguments (1 input and 1 output file)")
outFilename = args[-1]
inputFiles = args[:-1]
logging.debug("Using output file: %s" % outFilename)
logging.debug("Combining input files: %s" % str(inputFiles))

# find channel indices
def find_channel(filepath):
    m = re.match(options.regex, os.path.basename(filepath))
    if m is None:
        raise ValueError("No channel found for %s" % filepath)
    g = m.groups()
    if len(g) != 1:
        raise ValueError("Too many channels found for %s : %s" % (filepath, str(g)))
    try:
        return int(g[0])
    except:
        raise ValueError("Invalid (non-int) channel found for %s : %s" % (filepath, g[0]))
# find_channel = lambda filepath: int(re.match(options.regex, filepath).groups()[0])
channels = [find_channel(f) for f in inputFiles]
logging.debug("Channels: %s" % str(channels))

# open output file
logging.debug("Opening output file [%s] for writing" % outFilename)
outfile = tables.openFile(outFilename,'w')

# setup output file
logging.debug("creating output file groups")
channelsgroup = outfile.createGroup('/', 'Channels', 'SPC results')
spcgroup = outfile.createGroup('/', 'SPC', 'SPC results')
outfile.flush()

# add each input file
logging.debug("processing input files")
for (ch, f) in zip(channels, inputFiles):
    logging.debug("opening: %s" % f)
    infile = tables.openFile(f,'r')
    
    logging.debug("copying spike table")
    # SpikeTable/<wave/time/clu>
    stdescription = infile.root.SpikeTable.description
    spiketable = outfile.createTable(channelsgroup, 'ch%i' % ch, stdescription)
    for r in infile.root.SpikeTable:
        for k in stdescription._v_colObjects.keys():
            spiketable.row[k] =  r[k]
        spiketable.row.append()
    outfile.flush()
    
    logging.debug("copying spc results")
    # SPC/<cdata/ctree>
    spcg = outfile.createGroup(spcgroup, 'ch%i' % ch, 'Channel %i SPC results' % ch)
    infile.createArray(spcg, 'cdata', np.array(infile.root.SPC.cdata))
    infile.createArray(spcg, 'ctree', np.array(infile.root.SPC.ctree))
    outfile.flush()
    
    # meta data
    logging.debug("adding metadata")
    # original file
    spiketable.attrs.ORIGFILE = f
    logging.debug("closing: %s" % f)
    infile.close()

# close output file
logging.debug("closing: %s" % outFilename)
outfile.flush()
outfile.close()

# 
# 
# logging.basicConfig(level=logging.DEBUG)
# files = ['/Users/graham/Repositories/coxlab/physiology_analysis/data/pyc_input_3#01.wav/input_3#01.h5',
#         '/Users/graham/Repositories/coxlab/physiology_analysis/data/pyc_input_14#01.wav/input_14#01.h5']
# channels = [3, 14]
# outFilename = "foo.h5"
# 
# # find files
# optparse
# # determine channels
# 
# logging.debug("Opening output file [%s] for writing" % outFilename)
# outfile = tables.openFile(outFilename,'w')
# 
# logging.debug("creating output file groups")
# channelsgroup = outfile.createGroup('/', 'Channels', 'SPC results')
# spcgroup = outfile.createGroup('/', 'SPC', 'SPC results')
# outfile.flush()
# 
# logging.debug("processing input files")
# for (ch, f) in zip(channels, files):
#     logging.debug("opening: %s" % f)
#     infile = tables.openFile(f,'r')
#     
#     logging.debug("copying spike table")
#     # SpikeTable/<wave/time/clu>
#     stdescription = infile.root.SpikeTable.description
#     spiketable = outfile.createTable(channelsgroup, 'ch%i' % ch, stdescription)
#     for r in infile.root.SpikeTable:
#         for k in stdescription._v_colObjects.keys():
#             spiketable.row[k] =  r[k]
#         spiketable.row.append()
#     outfile.flush()
#     
#     logging.debug("copying spc results")
#     # SPC/<cdata/ctree>
#     spcg = outfile.createGroup(spcgroup, 'ch%i' % ch, 'Channel %i SPC results' % ch)
#     infile.createArray(spcg, 'cdata', np.array(infile.root.SPC.cdata))
#     infile.createArray(spcg, 'ctree', np.array(infile.root.SPC.ctree))
#     outfile.flush()
#     
#     # meta data
#     logging.debug("adding metadata")
#     # original file
#     spiketable.attrs.ORIGFILE = f
#     logging.debug("closing: %s" % f)
#     infile.close()
# 
# logging.debug("closing: %s" % outFilename)
# outfile.flush()
# outfile.close()