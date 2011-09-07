#!/usr/bin/env python

import logging, sys

import numpy as np

from .. import pixelclock

def test_find_transitions():
    t = np.linspace(0., 10., 101)
    f = 0.5
    x = np.sin(t * f * 2 * np.pi)
    p = np.where(x > 0, x, np.zeros_like(x))
    n = np.where(x < 0, x, np.zeros_like(x))
    a = np.abs(x)
    i = -a
    
    gi = pixelclock.find_transitions(a, 0.3, 1)
    assert all(gi == [ 0, 10, 20, 30, 40, 50, 60, 70, 80, 90])

def test_state_to_code():
    assert (pixelclock.state_to_code([1,1,1,1]) == 15)
    assert (pixelclock.state_to_code([0,1,1,1]) == 14)
    assert (pixelclock.state_to_code([1,0,1,1]) == 13)
    assert (pixelclock.state_to_code([0,0,1,1]) == 12)
    assert (pixelclock.state_to_code([1,1,0,1]) == 11)
    assert (pixelclock.state_to_code([0,1,0,1]) == 10)
    assert (pixelclock.state_to_code([1,0,0,1]) == 9)
    assert (pixelclock.state_to_code([0,0,0,1]) == 8) # MSB = 1
    assert (pixelclock.state_to_code([1,1,1,0]) == 7)
    assert (pixelclock.state_to_code([0,1,1,0]) == 6)
    assert (pixelclock.state_to_code([1,0,1,0]) == 5)
    assert (pixelclock.state_to_code([0,0,1,0]) == 4)
    assert (pixelclock.state_to_code([1,1,0,0]) == 3)
    assert (pixelclock.state_to_code([0,1,0,0]) == 2)
    assert (pixelclock.state_to_code([1,0,0,0]) == 1) # LSB = 1
    assert (pixelclock.state_to_code([0,0,0,0]) == 0)

def test_get_marker_delta():
    pcY = -28
    pcHeight = 8.5
    screenHeight = 64.54842055808264
    sepRatio = 0.2
    nchannels = 4
    delta = pixelclock.get_marker_delta(nchannels, pcY, pcHeight, screenHeight, sepRatio)
    target = 2.04
    # logging.debug("%s %s" % (str(delta),str(target)))
    assert np.abs(delta - target) < 0.0001, np.abs(delta - target)

def test_get_marker_positions():
    pcY = -28
    pcHeight = 8.5
    screenHeight = 64.54842055808264
    sepRatio = 0.2
    nchannels = 4
    # delta = pixelclock.get_marker_delta(nchannels, pcY, pcHeight, screenHeight, sepRatio)
    pos = pixelclock.get_marker_positions(nchannels, pcY, pcHeight, screenHeight, sepRatio)
    pos = np.array(pos)
    target = np.array([62.508, 60.468, 58.428, 56.388])
    assert np.abs(np.sum(pos - target)) < 0.01, np.abs(np.sum(pos-target))

def test_events_to_codes():
    codes = [15,4,9,11,2,1,7,12,3,4,6,2,1,2,5,15,0,2,1,6,2,4,6,8,2,4,6,8,2,6,4,8,9,0,7,4,3,5,7]
    times = [i*1000 for i in xrange(1,len(codes)+1)]
    # times = [1000, 2000, 3000, 4000, 5000, 6000]
    pcY = -28
    pcHeight = 8.5
    screenHeight = 64.54842055808264
    sepRatio = 0.2
    nchannels = 4
    refreshTime = 0.004
    samplerate = 44100
    
    positions = pixelclock.get_marker_positions(nchannels, pcY, pcHeight, screenHeight, sepRatio)
    positions = np.array(positions)
    refreshSpeed = screenHeight / refreshTime # degrees per second
    offsets = (positions / refreshSpeed) * samplerate # sample time of update for each marker
    # sys.stderr.write("%s\n" % str(offsets))
    
    offsets = np.round(offsets).astype('int')
    # sys.stderr.write("%s\n" % str(offsets))
    
    # markerSize = 1.0 / (nchannels + (nchannels+1) * sepRatio) * pcHeight
    # sepSize = sepRatio * markerSize
    # refreshSpeed = screenHeight / refreshTime
    # # logging.debug("MarkerSize: %.4f" % markerSize)
    # # logging.debug("Sep Size  : %.4f" % sepSize)
    # offsets = []
    # for i in xrange(nchannels):
    #     pos = screenHeight - (markerSize + sepSize) * (i+1)
    #     offset = (pos / refreshSpeed) * samplerate
    #     offsets.append(int(np.round(offset)))
    
    events = []
    lastCode = 8
    nchannels = 4
    bitmasks = [1, 2, 4, 8]
    for (c,t) in zip(codes,times):
        # line = "Code %i[%s] to %i[%s] ::" % (lastCode, bin(lastCode), c, bin(c))
        for i in xrange(nchannels):
            last = lastCode & bitmasks[i]
            new = c & bitmasks[i]
            if last != new:
                if new > last:
                    events.append((t+offsets[i], i, +1))
                    # line += " %i @ %i in %i" % (i, t+offsets[i], +1)
                else:
                    events.append((t+offsets[i], i, -1))
                    # line += " %i @ %i in %i" % (i, t+offsets[i], -1)
        lastCode = c
        # print line
    events = np.array(events)
    newCodes, latencies = pixelclock.events_to_codes(events, nchannels, 100)
    logging.debug('%s' % str(latencies))
    c = np.array(newCodes)[:,1]
    
    assert all(c == codes)
    
    offsetCodes, foundOffsets, avgSpeed = pixelclock.offset_codes(newCodes, latencies, pcY, pcHeight, screenHeight, sepRatio)
    logging.debug("Actual Offsets: %s" % str(offsets)) # [1, 4, 7, 10]
    logging.debug("Found  Offsets: %s" % str(foundOffsets))
    logging.debug("Actual Speed  : %s" % (screenHeight / (refreshTime*samplerate)))
    logging.debug("Found  Speed  : %s" % (avgSpeed))
    
    t = np.array(offsetCodes)[:,0]
    c = np.array(offsetCodes)[:,1]
    
    assert all(c == codes)
    
    # using + transitions = offsetCodes = later (1005)
    # using - transitions = offsetCodes = sooner (995)
    # this was fixed by using only latencies from patches far non-adjacent patches
    
    assert np.sum((t - np.array(times))) < (len(times)*2.), "%s" % offsetCodes