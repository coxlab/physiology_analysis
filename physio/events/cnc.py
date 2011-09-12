#import mworks.data as mw
import logging, sys

import numpy as np

from .. import utils
from .. import h5

def get_cnc_events(eventsFile, timeRange = None):
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
            utils.error("unknown probe offset string: %s" % offsetString, ValueError)
    if offset == None: utils.error("unknown probe offset string: %s" % offsetString, ValueError)
    return offset

def get_tip_offset(resultsFilename):
    with utils.H5Maker(resultsFilename, 'r') as resultsFile:
        probeDict = h5.utils.group_to_dictionary(resultsFile.getNode('/ProbeGData'))
    return offset_string_to_float(probeDict['offset'])

def get_channel_locations(cncDict, offset, time):
    eventNames = ['path_origin_x', 'path_origin_y', 'path_origin_z',
                    'path_slope_x', 'path_slope_y', 'path_slope_z',
                    'path_depth']
    current = {}
    for eventName in eventNames:
        print cncDict[eventName]
        for t, v in zip(*cncDict[eventName]):
            if t >= time: current[eventName] = float(v)
    
    if eventName in eventNames:
        if not (eventName in current.keys()):
            utils.error("cnc dict does not contain: %s" % str(eventName))
    
    origin = np.array([current['path_origin_x'], current['path_origin_y'], current['path_origin_z']])
    logging.debug("Path origin: %s" % str(origin))
    slope = np.array([current['path_slope_x'], current['path_slope_y'], current['path_slope_z']])
    logging.debug("Path slope: %s" % str(slope))
    depth = current['path_depth']
    logging.debug("Path depth: %s" % str(depth))
    
    tip = origin + slope * depth
    logging.debug("Tip location: %s" % str(tip))
    
    channels = [tip + slope * (o * 0.1 + 0.5 + offset) for o in xrange(32)]
    
    return channels

# def find_stable_epochs_in_events(eventDict, minTime=600, minDepth=-30):
#     """
#     Uses a eventDict found from read_cnc_from_mw to find period where the cnc was 'stable'
#     Each stable period must be at least minTime seconds long and
#     must be at a depth greater than minDepth
#     
#     at the moment only uses depth
#     """
#     t, d = eventDict['path_depth']
#     
#     epochs = []
#     
#     start_i = 0
#     for i in xrange(len(t)):
#         if d[i] != d[start_i]:
#             # calculate time since start of possible epoch
#             dt = t[i] - t[start_i]
#             if dt >= minTime and abs(d[start_i]) >= abs(minDepth):
#                 # add epoch
#                 epochs.append((t[start_i],t[i]))
#             start_i = i
#     return epochs

# def find_channel_positions(eventDict, epoch, tipOffset):
#     """
#     For a given epoch = (mw_start_time, mw_end_time), find the channel locations
#     """
#     t = np.array(eventDict['path_depth'][0])
#     epochStart, epochEnd = epoch
#     startIndex = abs(epochStart - t).argmin()
#     origin = np.array([eventDict['path_origin_%s' % s][1][startIndex] for s in ['x','y','z']])
#     logging.debug("Origin: %s" % str(origin))
#     slope = np.array([eventDict['path_slope_%s' % s][1][startIndex] for s in ['x','y','z']])
#     logging.debug("Slope: %s" % str(slope))
#     depth = eventDict['path_depth'][1][startIndex]
#     logging.debug("Depth: %s" % str(depth))
#     
#     tip_position = origin + slope * depth
#     #ML:6.413 AP:-7.912 DV:-4.846
#     tip_position = [6.413, -7.912, -4.846]
#     logging.debug("Tip: %s" % str(tip_position))
#     
#     pads = [tip_position + slope * (o * 0.1 + 0.5 + tipOffset) for o in xrange(32)]
#     
#     return pads
# 
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.DEBUG)
#     
#     import pylab as pl
#     mw_filename = '../data/K4_110523/K4_110523.mwk'
#     if len(sys.argv) > 1:
#         mw_filename = sys.argv[1]
#     
#     eventDict = read_cnc_from_mw(mw_filename)
#     
#     for eventName in eventDict.keys():
#         t, v = eventDict[eventName]
#         pl.plot(t,v,label=eventName)
#         pl.scatter(t,v)
#     pl.legend()
#     
#     epochs = find_stable_epochs_in_events(eventDict)
#     
#     for epoch in epochs:
#         pl.axvspan(epoch[0], epoch[1], facecolor='b', alpha=0.5)
#     
#     
#     tipOffset = 0.23
#     for epoch in epochs:
#         pl.figure()
#         positions = np.array(find_channel_positions(eventDict, epoch,tipOffset))
#         print "Epoch:", epoch
#         print "\tpads:", positions
#         #pl.autoscale(True)
#         pl.scatter(positions[:,0],positions[:,2])
#         pl.gca().autoscale_view()
#         pl.xlim((-8,8))
#         pl.ylim((-11,0))
#     
#     pl.show()
