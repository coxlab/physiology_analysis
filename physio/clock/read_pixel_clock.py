#!/usr/bin/env python

import copy, logging
from optparse import OptionParser

import numpy as np
import scikits.audiolab as al

import timebase

# output_file should contain /Events
parser = OptionParser(usage="usage: %prog [options] [pixel_clock_audio_files..(4x)] [output_file]")
parser.add_option("-v", "--verbose", dest = "verbose",
                    help = "enable verbose reporting",
                    default = False, action = "store_true")

(options, args) = parser.parse_args()
if options.verbose:
    logging.basicConfig(level=logging.DEBUG)

if len(args) != 5:
    logging.error("Must provide 4 pixel clock files and 1 output file")
    parser.print_usage()
    raise ValueError("Must provide 4 pixel clock files and 1 output file")

outFilename = args[-1]
audioFiles = args[:-1]

# parse pixel clock
