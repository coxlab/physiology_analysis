#!/usr/bin/env python

import ast, logging, re
from optparse import OptionParser

import numpy as np
import tables

from .. import utils

def find_events_group(eventsFile):#, regex = r'[a-z,A-Z]+[0-9]_[0-9]+'):
    """
    Find the h5file node that contains session events by looking for
    a group that contains codec, values, and events subnodes
    
    Parameters
    ----------
    eventsFile : hdf5 file object
        Hdf5 file object that contains session events
    
    Returns
    -------
    eventsgroup : hdf5 node
        Group within eventsFile that contains session events
    """
    # for k in eventsFile.root._v_children.keys():
    #     if re.match(regex, k):
    #         return eventsFile.getNode('/%s' % k)
    for node in eventsFile:
        if type(node) != tables.group.Group: continue
        if not ('codec' in node): continue
        if not ('values' in node): continue
        if not ('events' in node): continue
        return node

def get_codec(eventsFile):
    """
    Get the session events codec from an hdf5 results or events file
    
    Parameters
    ----------
    eventsFile : string or h5file
        Filename or file (used with utils.H5Maker) from which to read events
    
    Returns
    -------
    codec : dict
        Session events codec
    """
    with utils.H5Maker(eventsFile,'r') as f:
        g = find_events_group(f)
        codec = dict(g.codec.read())
    return codec

def parse_value(value):
    if value == '[null]': 
        return []
    if value == 'Infinity':
        return np.inf
    if value == 'NaN':
        return np.nan
    return ast.literal_eval(value)

def get_events(eventsFile, code, timeRange = None):
    """
    Parameters
    ----------
    eventsFile : string or h5file
        Filename or file (used with utils.H5Maker) from which to read events
    code : string or int
        Event code or name
    timeRange : 2 tuple of floats
        Range (in mworks time in seconds) over which to read events
    
    Returns
    -------
    times : list
        List of event times (in mworks times in second)
    values : list
        List of event values (processed with parse_value)
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
            evs = [(int(r['time']),g.values[r['index']]) for r in g.events.where('code == %i' % code)]
        else:
            # convert timeRange to microseconds
            timeRange = list(timeRange)
            timeRange[0] = int(timeRange[0] * 1E6)
            timeRange[1] = int(timeRange[1] * 1E6)
            # PyTables version 2.2.1 does not support selection on uint64 (the time type) so...
            assert np.iterable(timeRange), "timeRange[%s] must be iterable" % str(timeRange)
            assert len(timeRange) == 2, "timeRange length[%i] must be 2" % len(timeRange)
            assert type(timeRange[0]) == int, "timeRange[0] type[%s] must be int" % type(timeRange[0])
            evs = [(int(r['time']),g.values[r['index']]) for r in g.events.where('code == %i' % code) if \
                        int(r['time']) > timeRange[0] and int(r['time']) <= timeRange[1]]
    
    if len(evs) == 0: return np.array([]), []
    # vs = evs[:,1]
    # f.close()
    
    #times = np.array(evs[:,0],dtype=float) / float(1E6)
    # times = evs[:,0].astype(float) / float(1E6)
    times = np.array([int(ev[0]) for ev in evs], dtype = float) / float(1E6)
    values = [parse_value(ev[1]) for ev in evs]
    
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

