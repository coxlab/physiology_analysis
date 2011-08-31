#!/usr/bin/env python

import logging, re
from optparse import OptionParser

# import numpy as np
import tables

parser = OptionParser(usage="usage: %prog [options] [event_h5_file] [data_h5_file]")
parser.add_option("-r", "--regex", dest = "regex",
                    help = "regex (containing 1 group) to find channel from filename",
                    default = r'[a-z,A-Z]+[0-9]_[0-9]+')
parser.add_option("-v", "--verbose", dest = "verbose",
                    help = "enable verbose reporting",
                    default = False, action = "store_true")

(options, args) = parser.parse_args()
if options.verbose:
    logging.basicConfig(level=logging.DEBUG)

# parse args
assert len(args) > 1, ValueError("Must supply at least 2 arguments (1 event and 1 data file)")
eventFilename = args[0]
dataFilename = args[1]
logging.debug("Copying events from %s to %s" % (eventFilename, dataFilename))

dataFile = tables.openFile(dataFilename, 'a')
eventFile = tables.openFile(eventFilename, 'r')

# find event group
eventGroupname = None
for k in eventFile.root._v_children.keys():
    if re.match(options.regex, k):
        eventGroupname = k
assert not (eventGroupname is None), "No event group found for regex: %s" % options.regex
logging.debug('Found event group name: %s' % eventGroupname)

eventGroup = eventFile.getNode('/%s' % eventGroupname)

# check if events group exists, if so, delete it
if 'Events' in dataFile.root._v_children.keys():
    logging.debug("File contains /Events table, removing table...")
    dataFile.removeNode('/Events', recursive = True)

outGroup = dataFile.createGroup('/', 'Events', '')

# copy codec
logging.debug("Copying codec")
desc = eventGroup.codec.description
codecOut = dataFile.createTable(outGroup, 'codec', eventGroup.codec.description)
for r in eventGroup.codec:
    for k in desc._v_colObjects.keys():
        codecOut.row[k] =  r[k]
    codecOut.row.append()
dataFile.flush()

# copy events
logging.debug("Copying events")
desc = eventGroup.events.description
eventsOut = dataFile.createTable(outGroup, 'events', eventGroup.events.description)
for r in eventGroup.events:
    for k in desc._v_colObjects.keys():
        eventsOut.row[k] =  r[k]
    eventsOut.row.append()
dataFile.flush()

# values = VLArray
logging.debug("Copying values")
valuesOut = dataFile.createVLArray(outGroup, 'values', tables.VLStringAtom(), "Values", expectedsizeinMB=0.0001)
for v in eventGroup.values:
    valuesOut.append(v)
dataFile.flush()

logging.debug("Cleaning up")
dataFile.close()
eventFile.close()