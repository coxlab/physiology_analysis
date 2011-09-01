#!/usr/bin/env python

import ast, logging, re
from optparse import OptionParser

import numpy as np
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
    eventsgroup : hdf5 node
        Group within eventsFile that contains session events
    """
    for k in eventsFile.root._v_children.keys():
        if re.match(regex, k):
            return eventsFile.getNode('/%s' % k)

def read_events(eventsFile, code, timeRange = None):
    """
    Parameters
    ----------
    eventsFile : string or h5file
        Filename or file (used with utils.H5Maker) from which to read events
    code : string or int
        Event code or name
    timerange : 2 tuple of ints
        Range (in mworks time in seconds) over which to read events
    
    Returns
    -------
    times : list
        List of event times (in mworks times in second)
    values : list
        List of event values (processed with ast.literal_eval)
    """
    # f = tables.openFile(eventsFilename,'r')
    with utils.H5Maker(eventsFile,'r') as f:
        g = find_events_group(f)
        
        # lookup code if it is not an int
        if type(code) != int:
            codec = dict(g.codec.read())
            if not (code in codec.values()): utils.error('code[%s] not found in codec: %s' % (code, str(codec)))
            code = codec.keys()[codec.values().index(code)]
        
        if timeRange is None:
            evs = np.array([(int(r['time']),g.values[r['index']]) for r in g.events.where('code == %i' % code)])
        else:
            # convert timerange to microseconds
            timeRange[0] = int(timeRange[0] * 1E6)
            timeRange[1] = int(timeRange[1] * 1E6)
            # PyTables version 2.2.1 does not support selection on uint64 (the time type) so...
            assert np.iterable(timeRange), "timeRange[%s] must be iterable" % str(timeRange)
            assert len(timeRange) == 2, "timeRange length[%i] must be 2" % len(timeRange)
            assert type(timeRange[0]) == int, "timeRange[0] type[%s] must be int" % type(timerange[0])
            evs = np.array([(int(r['time']),g.values[r['index']]) for r in g.events.where('code == %i' % code) if \
                        int(r['time']) > timeRange[0] and int(r['time']) <= timeRange[1]])
    vs = evs[:,1]
    # f.close()
    
    times = np.array(evs[:,0],dtype=float) / float(1E6)
    values = [ast.literal_eval(v) for v in vs]
    
    return times, values

def add_events_file(eventsFilename, dataFilename):
    """
    Copy events from one hdf5 file (events file) to another (data file)
    
    Parameters
    ----------
    eventFilename : string or h5file
         Filename or file (used with utils.H5Maker) containing session events
    dataFilename : string
         Filename or file (used with utils.H5Maker) containing other session data (spike events, etc...)
    """
    # eventsFile = tables.openFile(eventsFilename, 'r')
    # dataFile = tables.openFile(dataFilename, 'a') # make sure this is append and not write
    with utils.H5Maker(eventsFilename, 'r') as eventsFile:
        with utils.H5Maker(dataFilename, 'a') as dataFile:
            # find event group
            #eventsGroupName = find_events_group(eventsFile)
            #eventsGroup = eventsFile.getNode('/%s' % eventsGroupName)
            eventsGroup = find_events_group(eventsFile)
            
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
    
    # logging.debug("Cleaning up")
    # dataFile.close()
    # eventsFile.close()
    return

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
