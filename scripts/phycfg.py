#!/usr/bin/env python

import logging, optparse

import physio

parser = optparse.OptionParser(usage="usage: %prog <section> <variable>")
parser.add_option("-v", "--verbose", dest = "verbose",
        help = "enable verbose reporting",
        default = False, action = "store_true")
(options, args) = parser.parse_args()

if len(args) != 2:
    parser.print_usage()
    raise ValueError("Must supply <section> and <variable> names")

if options.verbose:
    logging.basicConfig(level = logging.DEBUG)
else:
    logging.basicConfig(level = logging.ERROR)

section, variable = args

config = physio.cfg.Config()
config.read_user_config()

try:
    value = config.get(section, variable)
    print value
except Exception as E:
    logging.error("Exception: %s" % str(E))
    print "Error"
