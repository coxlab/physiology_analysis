#!/usr/bin/env python

import logging, re
from optparse import OptionParser

# import numpy as np
import tables

from .. import utils

def find_events_group(eventsFile, regex = r'[a-z,A-Z]+[0-9]_[0-9]+'):
    """
    Determine the name of the group in which events are stored by matching
    against a regular expression
    
    Parameters
    ----------
    eventsFile : hdf5 file object
        Hdf5 file object that contains session events
    regex : string
        Regex used to find group that contains session events
    
    Returns
    -------
    eventsgroup : string
        Group within eventsFile that contains session events
    """
    for k in eventFile.root._v_children.keys():
        if re.match(options.regex, k):
            return k

def read_events(eventsFilename, code, timeRange = None):
    """
    timerange in mw time in microseconds
    """
    f = tables.openFile(eventsFilename,'r')
    g = find_events_group(f)
    
    # lookup code if it is not an int
    if type(code) != int:
        codec = dict(g.codec.read())
        if not (code in codec.values()): utils.error('code[%s] not found in codec: %s' % (code, str(codec)))
        code = codec.keys()[codec.values().index(code)]
    
    if timeRange is None:
        evs = np.array([(r['time'],r['index']) for r in g.events.where('code == %i')])
    else:
        # PyTables version 2.2.1 does not support selection on uint64 (the time type) so...
        assert iterable(timeRange), "timeRange[%s] must be iterable" % str(timeRange)
        assert len(timeRange) == 2, "timeRange length[%i] must be 2" % len(timeRange)
        assert type(timeRange[0]) == int, "timeRange[0] type[%s] must be int" % type(timerange[0])
        evs = np.array([(r['time'],r['index']) for r in g.events.where('code == %i') if \
                    e['time'] > timeRange[0] and e['time'] <= timeRange[1]])
    vs = g.values[evs[:,1]]
    f.close()
    
    times = evs[:,0] / 1E6
    values = [ast.literal_eval(v) for v in vs]
    
    return times, values

def add_events_file(eventsFilename, dataFilename):
    """
    Copy events from one hdf5 file (events file) to another (data file)
    
    Parameters
    ----------
    eventFilename : string
        Path of file containing session events
    dataFilename : string
        Path of file containing other session data (spike events, etc...)
    """
    eventsFile = tables.openFile(eventsFilename, 'r')
    dataFile = table.openFile(dataFilename, 'a') # make sure this is append and not write
    
    # find event group
    eventsGroupName = find_events_group(eventsFile)
    eventsGroup = eventsFile.getNode('/%s' % eventsGroupName)
    
    # check if events group exists, if so, delete it
    if 'Events' in dataFile.root._v_children.keys():
        logging.debug("File contains /Events table, removing table...")
        dataFile.removeNode('/Events', recursive = True)
    
    outGroup = dataFile.createGroup('/', 'Events', '')
    
    # copy codec
    logging.debug("Copying codec")
    desc = eventsGroup.codec.description
    codecOut = dataFile.createTable(outGroup, 'codec', eventsGroup.codec.description)
    for r in eventsGroup.codec:
        for k in desc._v_colObjects.keys():
            codecOut.row[k] =  r[k]
        codecOut.row.append()
    dataFile.flush()
    
    # copy events
    logging.debug("Copying events")
    desc = eventsGroup.events.description
    eventsOut = dataFile.createTable(outGroup, 'events', eventsGroup.events.description)
    for r in eventsGroup.events:
        for k in desc._v_colObjects.keys():
            eventsOut.row[k] =  r[k]
        eventsOut.row.append()
    dataFile.flush()
    
    # values = VLArray
    logging.debug("Copying values")
    valuesOut = dataFile.createVLArray(outGroup, 'values', tables.VLStringAtom(), "Values", expectedsizeinMB=0.0001)
    for v in eventsGroup.values:
        valuesOut.append(v)
    dataFile.flush()
    
    logging.debug("Cleaning up")
    dataFile.close()
    eventsFile.close()

# # -------- Old -----------
# 
# parser = OptionParser(usage="usage: %prog [options] [event_h5_file] [data_h5_file]")
# parser.add_option("-r", "--regex", dest = "regex",
#                     help = "regex (containing 1 group) to find channel from filename",
#                     default = r'[a-z,A-Z]+[0-9]_[0-9]+')
# parser.add_option("-v", "--verbose", dest = "verbose",
#                     help = "enable verbose reporting",
#                     default = False, action = "store_true")
# 
# (options, args) = parser.parse_args()
# if options.verbose:
#     logging.basicConfig(level=logging.DEBUG)
# 
# # parse args
# assert len(args) > 1, ValueError("Must supply at least 2 arguments (1 event and 1 data file)")
# eventFilename = args[0]
# dataFilename = args[1]
# logging.debug("Copying events from %s to %s" % (eventFilename, dataFilename))
# 
# dataFile = tables.openFile(dataFilename, 'a')
# eventFile = tables.openFile(eventFilename, 'r')
# 
# # find event group
# eventGroupname = None
# for k in eventFile.root._v_children.keys():
#     if re.match(options.regex, k):
#         eventGroupname = k
# assert not (eventGroupname is None), "No event group found for regex: %s" % options.regex
# logging.debug('Found event group name: %s' % eventGroupname)
# 
# eventGroup = eventFile.getNode('/%s' % eventGroupname)
# 
# # check if events group exists, if so, delete it
# if 'Events' in dataFile.root._v_children.keys():
#     logging.debug("File contains /Events table, removing table...")
#     dataFile.removeNode('/Events', recursive = True)
# 
# outGroup = dataFile.createGroup('/', 'Events', '')
# 
# # copy codec
# logging.debug("Copying codec")
# desc = eventGroup.codec.description
# codecOut = dataFile.createTable(outGroup, 'codec', eventGroup.codec.description)
# for r in eventGroup.codec:
#     for k in desc._v_colObjects.keys():
#         codecOut.row[k] =  r[k]
#     codecOut.row.append()
# dataFile.flush()
# 
# # copy events
# logging.debug("Copying events")
# desc = eventGroup.events.description
# eventsOut = dataFile.createTable(outGroup, 'events', eventGroup.events.description)
# for r in eventGroup.events:
#     for k in desc._v_colObjects.keys():
#         eventsOut.row[k] =  r[k]
#     eventsOut.row.append()
# dataFile.flush()
# 
# # values = VLArray
# logging.debug("Copying values")
# valuesOut = dataFile.createVLArray(outGroup, 'values', tables.VLStringAtom(), "Values", expectedsizeinMB=0.0001)
# for v in eventGroup.values:
#     valuesOut.append(v)
# dataFile.flush()
# 
# logging.debug("Cleaning up")
# dataFile.close()
# eventFile.close()