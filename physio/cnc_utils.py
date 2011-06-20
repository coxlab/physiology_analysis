#import mworks.data as mw
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

if __name__ == '__main__':
    import pylab as pl
    mw_filename = '../data/K4_110523/K4_110523.mwk'
    
    eventDict = read_cnc_from_mw(mw_filename)
    
    for eventName in eventDict.keys():
        t, v = eventDict[eventName]
        pl.plot(t,v,label=eventName)
        pl.scatter(t,v)
    pl.legend()
    
    epochs = find_stable_epochs_in_events(eventDict)
    
    # should be [(2075.8280759999998, 5771.5493690000003)]
    print epochs
    
    for epoch in epochs:
        pl.axvspan(epoch[0], epoch[1], facecolor='b', alpha=0.5)
    
    pl.show()
