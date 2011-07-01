#import mworks.data as mw
import logging, sys

import numpy as np

import mw_utils

def read_cnc_from_mw(mw_filename, eventNames=[ \
                                'path_origin_x', 'path_origin_y', 'path_origin_z',\
                                'path_slope_x', 'path_slope_y', 'path_slope_z',\
                                'path_depth']):
    """
    Returns a dict of cnc event data (path, slope, depth) with:
        keys = eventNames
        values = (eventTimes, eventValues)
    """
    # f = mw.MWKFile(mw_filename)
    f = mw_utils.make_reader(mw_filename)
    f.open()
    
    resultDict = {}
    
    for eventName in eventNames:
        events = f.get_events(codes=[eventName])
        times = [e.time / 1E6 for e in events]
        values = [e.value for e in events]
        resultDict[eventName] = (times, values)
    
    f.close()
    
    return resultDict

def find_stable_epochs_in_events(eventDict, minTime=600, minDepth=-30):
    """
    Uses a eventDict found from read_cnc_from_mw to find period where the cnc was 'stable'
    Each stable period must be at least minTime seconds long and
    must be at a depth greater than minDepth
    
    at the moment only uses depth
    """
    t, d = eventDict['path_depth']
    
    epochs = []
    
    start_i = 0
    for i in xrange(len(t)):
        if d[i] != d[start_i]:
            # calculate time since start of possible epoch
            dt = t[i] - t[start_i]
            if dt >= minTime and abs(d[start_i]) >= abs(minDepth):
                # add epoch
                epochs.append((t[start_i],t[i]))
            start_i = i
    return epochs

def find_channel_positions(eventDict, epoch, tipOffset):
    """
    For a given epoch = (mw_start_time, mw_end_time), find the channel locations
    """
    t = np.array(eventDict['path_depth'][0])
    epochStart, epochEnd = epoch
    startIndex = abs(epochStart - t).argmin()
    origin = np.array([eventDict['path_origin_%s' % s][1][startIndex] for s in ['x','y','z']])
    logging.debug("Origin: %s" % str(origin))
    slope = np.array([eventDict['path_slope_%s' % s][1][startIndex] for s in ['x','y','z']])
    logging.debug("Slope: %s" % str(slope))
    depth = eventDict['path_depth'][1][startIndex]
    logging.debug("Depth: %s" % str(depth))
    
    tip_position = origin + slope * depth
    #ML:6.413 AP:-7.912 DV:-4.846
    tip_position = [6.413, -7.912, -4.846]
    logging.debug("Tip: %s" % str(tip_position))
    
    pads = [tip_position + slope * (o * 0.1 + 0.5 + tipOffset) for o in xrange(32)]
    
    return pads

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    import pylab as pl
    mw_filename = '../data/K4_110523/K4_110523.mwk'
    if len(sys.argv) > 1:
        mw_filename = sys.argv[1]
    
    eventDict = read_cnc_from_mw(mw_filename)
    
    for eventName in eventDict.keys():
        t, v = eventDict[eventName]
        pl.plot(t,v,label=eventName)
        pl.scatter(t,v)
    pl.legend()
    
    epochs = find_stable_epochs_in_events(eventDict)
    
    for epoch in epochs:
        pl.axvspan(epoch[0], epoch[1], facecolor='b', alpha=0.5)
    
    
    tipOffset = 0.23
    for epoch in epochs:
        pl.figure()
        positions = np.array(find_channel_positions(eventDict, epoch,tipOffset))
        print "Epoch:", epoch
        print "\tpads:", positions
        pl.autoscale(True)
        pl.scatter(positions[:,0],positions[:,2])
        pl.gca().autoscale_view()
        pl.xlim((-8,8))
        pl.ylim((-11,0))
    
    pl.show()
