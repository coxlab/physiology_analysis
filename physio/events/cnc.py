#import mworks.data as mw
import logging

import numpy as np

from .. import channelmapping
from .. import h5
from .. import utils

eventNames = ['path_origin_x', 'path_origin_y', 'path_origin_z',
                'path_slope_x', 'path_slope_y', 'path_slope_z',
                'path_depth']


def get_location_override(eventsFile):
    # return dictionary with keys = eventNames or None
    override = None
    with utils.H5Maker(eventsFile, 'r') as f:
        if 'LOCATION' in f.root.Events._v_attrs._v_attrnames:
            loc = f.root.Events._v_attrs['LOCATION']
            override = dict(zip(eventNames, loc))
    return override


def get_cnc_events(eventsFile, timeRange=None):
    eventNames = ['path_origin_x', 'path_origin_y', 'path_origin_z',
                    'path_slope_x', 'path_slope_y', 'path_slope_z',
                    'path_depth']
    cncDict = {}
    for eventName in eventNames:
        times, values = h5.events.get_events(eventsFile, eventName, timeRange)
        cncDict[eventName] = (times, values)

    return cncDict


def offset_string_to_float(offsetString):
    offset = None
    try:
        offset = float(offsetString)
    except:
        try:
            offset = float(offsetString.split()[0])
        except:
            utils.error("unknown probe offset string: %s" % offsetString, \
                    ValueError)
    if offset == None:
        utils.error("unknown probe offset string: %s" % offsetString, \
                ValueError)
    return offset


def get_tip_offset(resultsFilename):
    with utils.H5Maker(resultsFilename, 'r') as resultsFile:
        probeDict = h5.utils.group_to_dictionary(resultsFile.getNode(\
                '/ProbeGData'))
    return offset_string_to_float(probeDict['offset'])


def get_channel_locations(cncDict, offset, time, override=None):
    eventNames = ['path_origin_x', 'path_origin_y', 'path_origin_z',
                    'path_slope_x', 'path_slope_y', 'path_slope_z',
                    'path_depth']
    if override is None:
        current = {}
        for eventName in eventNames:
            # print cncDict[eventName]
            tvs = np.array(cncDict[eventName])  # [time/value, eventindex]
            # sort tvs by time
            tvs = tvs[:, tvs[0].argsort()]
            for t, v in zip(tvs[0], tvs[1]):
                if t >= time:
                    break
                current[eventName] = float(v)
                logging.warning("cnc matched time %f to %f" % (time, t))
    else:
        current = override

    for eventName in eventNames:
        if not (eventName in current.keys()):
            utils.error("cnc dict does not contain: %s" % str(eventName))

    origin = np.array([current['path_origin_x'], current['path_origin_y'], \
            current['path_origin_z']])
    logging.debug("Path origin: %s" % str(origin))
    slope = np.array([current['path_slope_x'], current['path_slope_y'], \
            current['path_slope_z']])
    logging.debug("Path slope: %s" % str(slope))
    depth = current['path_depth']
    logging.debug("Path depth: %s" % str(depth))

    tip = origin + slope * depth
    logging.debug("Tip location: %s" % str(tip))

    # channels = [tip + slope * (o * 0.1 + 0.5 + offset) for o in xrange(32)]
    channels = [origin + slope * (depth + (o * 0.1 + 0.05 + offset)) \
            for o in xrange(32)]

    # remap to tdt order
    tdt = []
    for i in xrange(1, 33):
        chi = channelmapping.tdt_to_position(i)
        tdt.append(channels[chi])

    return tdt


def find_stable_epochs(depthTimes, depthValues, minTime=600, minDepth=-30):
    """
    Find long periods where the probe was stationary and below a certain depth

    Parameters
    ---------
    depthTimes : array of floats
        Times at path_depth events (in seconds)
    depthValues : array of floats
        Values at path_depth events
    minTime : float
        Minimum time (in seconds) of an epoch
    minDepth : float
        Only count epochs at a depth more extreme (more negative)
        than this value

    Returns
    -------
    epochs : array of arrays
        Array of epochs where each epoch is a list of:
            epoch[0] = time of starting depth event (in seconds)
            epoch[1] = time of ending depth event (in seconds)
            epoch[2] = depth value at starting depth event

    Notes
    -----
    Epoch times will ahve the same unit as depthTimes
    """
    assert len(depthTimes) == len(depthValues),\
        "depthTimes[%i] and depthValues[%i] must be the same length" % \
        (len(depthTimes), len(depthValues))

    nEvents = len(depthTimes)
    prevDepth = depthValues
    prevTime = depthTimes
    epochs = []
    for i in xrange(nEvents):
        # if the values are the same, assume you didn't move
        if prevDepth == depthValues[i]:
            continue
        if ((depthTimes[i] - prevTime) > minTime) and (prevDepth < minDepth):
            epochs.append([prevTime, depthTimes[i], prevDepth])
        prevTime = depthTimes[i]
        prevDepth = depthValues[i]

    return epochs
