#!/usr/bin/env python

import ast, copy, logging, warnings

import numpy as np
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import scikits.audiolab as al
# import tables

from .. import h5
from .. import dsp
from .. import utils

# 0 is LSB - 3 is MSB
# update is bottom -> up so add the most to channel 1
# 0 is first - 3 is last
# self.auChannelOffsets = [86, 84, 81, 79] # [2,5,7,9]
# size should be 8.5 degrees NOT 2.5 (as the clock is rotated 90 degrees)
#
# our monitor is a Sharp LC-42D43U
# resolution = 1360 x 768
# refresh rates =
#  horizontal = 47.7 kHz
#  vertical = 60 Hz
#  w x y in mm = 930 x 525
#  overscan is on : check that this is not clipping parts of the display
#  quoted : 6 ms response time (seems to be somewhat faster)
#  height in mworks 'degrees' 64.54842055808264
#  so...
#   ~ 10758.070093013774 degrees per second
#   ~ 0.24394716764203569 degrees per sample

def find_transitions(signal, threshold = 0.03, refractory = 44):
    """
    Find pixel clock transitions
    
    Parameters
    ----------
    signal : 1d array
        Signal in which to find threshold crossings
    threshold : float
        Threshold at which to find crossings (test: abs(signal) > threshold)
    refractory : int
        Number of sub-threshold points that must be encountered before resetting the trigger
    
    Returns
    -------
    crossings : 1d array
        Indicies where the signal crosses the threshold
    """
    crossings = dsp.peaks.find_both_threshold_crossings(signal, threshold, refractory)
    # return crossings
    return dsp.peaks.refine_crossings(signal, crossings)

def state_to_code(state):
    """
    Convert a pixel clock state list to a code
    
    Parameters
    ----------
    state : list
        List of 0s and 1s indicating the state of the pixel clock channels.
        state[0] = LSB, state[1] = MSB
    
    Returns
    -------
    code : int
        Reconstructed pixel clock code
    """
    return sum([state[i] << i for i in xrange(len(state))])

def events_to_codes(events, nchannels, minCodeTime):
    """
    Parameters
    ----------
    events : 2d array
        Array of pixel clock events (single channel transitions) where:
            events[:,0] = times
            events[:,1] = channels
            events[:,2] = directions
    nchannels : int
        Number of pixel clock channels
    minCodeTime : int
        Minimum time (in samples) for a given code change
    
    Return
    ------
    codes : 2d array
        Array of reconstructed pixel clock codes where:
            codes[:,0] = time
            codes[:,1] = code
            codes[:,2] = trigger channel
        These codes are NOT offset for latencies of the triggered channel
    latencies : nchannels x nchannels list of lists
        List of channel-to-channel latencies measured from events.
        Should be used with offset_codes to correct code times for the triggered channel
    """
    assert len(events) > 0, "Events cannot be 0 length"
    assert len(events[0]) == 3, "Each event should be of length 3 not %i" % len(events[0])
    # nchannels = len(channels)
    # times = np.hstack(times)
    # channels = np.hstack(channels)
    # directions = np.hstack(directions)
    evts = np.array(copy.deepcopy(events))
    # events = np.transpose(np.vstack((np.hstack(times),\
    #                                 np.hstack(channels),\
    #                                 np.hstack(directions))))
    evts = evts[evts[:,0].argsort(),:] # sort events
    # get initial state by looking at first transitions
    state = []
    for i in xrange(nchannels):
        d = evts[np.where(evts[:,1] == i)[0][0],2]
        if d == 1:
            state.append(0)
        else:
            state.append(1)
    # logging.debug("Initial state: %s = %i" % (state, state_to_code(state)))
    # print evts
    # print "Initial state: %s = %i" % (state, state_to_code(state))
    trigTime = evts[0,0]
    trigChannel = int(evts[0,1])
    trigDirection = int(evts[0,2])
    codes = []
    
    latencies = [ [ [] for x in xrange(nchannels)] for y in xrange(nchannels)]
    for ev in evts:
        if abs(ev[0] - trigTime) > minCodeTime:
            # new event
            code = state_to_code(state)
            codes.append((trigTime, code, trigChannel))
            trigTime = ev[0]
            trigChannel = int(abs(ev[1]))
            trigDirection = int(ev[2])
        # update state
        ch = int(abs(ev[1]))
        state[ch] += int(ev[2])
        if not (state[ch] in [0,1]):
            logging.debug("Invalid state found[%s] at %i, truncating" % (str(state), ev[0]))
            state[ch] = max(0,min(1,state[ch]))
        else:
            # only store on valid states and + transitions
            # TODO look at transition direction of trigger, did it go up or down? only look for THOSE events
            if (trigDirection == 1) and (int(ev[2]) == 1): latencies[trigChannel][ch].append(ev[0] - trigTime)
    
    # assume last code was complete
    code = state_to_code(state)
    if code != codes[-1][1]:
        codes.append((trigTime, code, trigChannel))
    
    return codes, latencies

def get_marker_delta(nchannels, pcY, pcHeight, screenHeight, sepRatio):
    markerSize = 1.0 / float(nchannels + (nchannels+1) * sepRatio)
    sepSize = sepRatio * markerSize
    markerDegrees = pcHeight * markerSize
    sepDegrees = pcHeight * sepSize
    return markerDegrees + sepDegrees

def get_marker_positions(nchannels, pcY, pcHeight, screenHeight, sepRatio):
    if pcY != -28: raise ValueError("Pixel clock is assumed to be at bottom of screen")
    delta = get_marker_delta(nchannels, pcY, pcHeight, screenHeight, sepRatio)
    pos = [screenHeight - (delta * (i+1)) for i in xrange(nchannels)]
    logging.debug("Pixel Clock Postions: %s" % str(pos))
    return pos

def offset_codes(codes, latencies, pcY, pcHeight, screenHeight, sepRatio):
    """
    Offset pixel clock code changes using the triggered channels measured onset latency
    
    Parameters
    ----------
    codes : 2d array
        Array of reconstructed pixel clock codes where:
            codes[:,0] = time
            codes[:,1] = code
            codes[:,2] = trigger channel
        These codes are NOT offset for latencies of the triggered channel
    latencies : nchannels x nchannels list of lists
        List of channel-to-channel latencies measured from events.
    pcY : float
        Vertical position of pixel clock on screen in degrees
    pcHeight : float
        Vertical size of pixel clock in degrees. This may be XScale if pixel clock is rotated
    screenHeight : float
        Vertical size of screen in degrees
    sepRatio : float
        Seperation ratio of pixel clock patches (see MWorks for more information)
    
    Returns
    -------
    codes : 2d array
        Array of reconstructed and offset pixel clock codes where:
            codes[:,0] = time
            codes[:,1] = code
            codes[:,2] = trigger channel
        These codes are NOT offset for latencies of the triggered channel
    offsets : list
        Offset times (in samples) for the onset of the pixel clock patch display relative
        to the bottom of the screen (the begging of the screen update)
    avgSpeed : float
        Average speed of screen refresh in degrees per sample
    
    Notes
    -----
    TODO: offset pixel clock from bottom of screen
    """
    
    nchannels = len(latencies)
    positions = get_marker_positions(nchannels, pcY, pcHeight, screenHeight, sepRatio)
    delta = get_marker_delta(nchannels, pcY, pcHeight, screenHeight, sepRatio)
    # markerSize = 1.0 / float(nchannels + (nchannels+1) * sepRatio)
    # sepSize = sepRatio * markerSize
    # markerDegrees = pcHeight * markerSize
    # sepDegrees = pcHeight * sepSize
    # # logging.debug("MarkerDs: %.4f" % markerDegrees)
    # # logging.debug("Sep   Ds: %.4f" % sepDegrees)
    # 
    # posDeltaDegrees = markerDegrees + sepDegrees # spacing between pixel clock patch bottom edges
    # posDegrees = [] # bottom edge of on screen pixel clock patches
    # for i in xrange(nchannels):
    #     posDegrees.append(screenHeight - (posDeltaDegrees * (i+1)))
    
    # avgSpeeds = np.zeros((nchannels,nchannels))
    allSpeeds = []
    
    for x in xrange(nchannels):
        for y in xrange(nchannels):
            if abs(x - y) < 2: continue # only use latencies for non-adjacent patches
            wt = abs(x - y) * delta
            if wt == 0:
                continue
            speeds = np.array(latencies[x][y]) / wt
            allSpeeds = np.hstack((allSpeeds, speeds))
    
    # # TODO remove this
    # import pickle
    # f = open('latencies.p','w')
    # pickle.dump(latencies,f)
    # f.close()
    # np.savetxt('allspeeds',allSpeeds)
    
    avgSpeed = np.mean(allSpeeds) # avgSpeed in samples per degree
    print allSpeeds
    # offsets = (np.array(posDegrees) * avgSpeed).astype(int)
    offsets = np.array(positions) * avgSpeed
    offsets = np.round(offsets).astype(int)
    
    codeArray = np.array(copy.deepcopy(codes))
    for i in xrange(len(codes)):
        channel = codeArray[i,2]
        codeArray[i,0] = codeArray[i,0] - offsets[channel]
    
    if avgSpeed != 0: # make this degrees per sample NOT samples per degree
        avgSpeed = 1. / avgSpeed
    logging.debug("Avg screen update speed in degrees per sample: %f" % avgSpeed)
    logging.debug("Pixel clock channel offsets in samples: %s" % str(offsets))
    return codeArray, offsets, avgSpeed

def reconstruct_codes(events, nchannels = 4, minCodeTime = 441,\
                    pcY = -28, pcHeight = 8.5, screenHeight = 64.54842055808264, sepRatio = 0.2):
    """
    Parameters
    ----------
    events : 2d array
        Array of pixel clock events (single channel transitions) where:
            events[:,0] = times
            events[:,1] = channels
            events[:,2] = directions
    nchannels : int
        Number of pixel clock channels
    minCodeTime : int
        Minimum time (in samples) for a given code change
    pcY : float
        Vertical position of pixel clock on screen in degrees
    pcHeight : float
        Vertical size of pixel clock in degrees. This may be XScale if pixel clock is rotated
    screenHeight : float
        Vertical size of screen in degrees
    sepRatio : float
        Seperation ratio of pixel clock patches (see MWorks for more information)
    
    Returns
    -------
    codes : 2d array
        Array of reconstructed and offset pixel clock codes where:
            codes[:,0] = time
            codes[:,1] = code
            codes[:,2] = trigger channel
    offsets : list
        Offset times (in samples) for the onset of the pixel clock patch display relative
        to the top of the screen (the beginning of the screen update)
    avgSpeed : float
        Average speed of screen refresh in degrees per sample
    """
    codes, latencies = events_to_codes(events, nchannels, minCodeTime)
    codes, offsets, avgSpeed = offset_codes(codes, latencies, pcY, pcHeight, screenHeight, sepRatio)
    return codes, offsets, avgSpeed

def match_test(au, mw, minMatch, maxErr):
    """
    Test if two codes sequeces match based on a minimum match length and maximum error
    
    Parameters
    ----------
    au : list
        List of audio codes to match
    mw : list
        List of mworks codes to match
    minMatch : int
        Minimum match length (starting at the first index)
    maxErr : int
        Maximum number of matching errors
    
    Returns
    -------
    match : bool
        True if codes matched, false if otherwise
    """
    mwI = 0
    auI = 0
    if len(mw) < minMatch or len(au) < minMatch:
        return False
    err = 0
    matchLen = 0
    while (mwI < len(mw)) and (auI < len(au)):
        if mw[mwI] == au[auI]:
            matchLen += 1
            if matchLen >= minMatch:
                # print "match!"
                return True
            mwI += 1
            auI += 1
        else:
            auI += 1
            err += 1
            if err > maxErr:
                # print "err"
                return False
    return False

def match_codes(auTimes, auCodes, mwTimes, mwCodes, minMatch = 10, maxErr = 0):
    """
    Find times of matching periods in two code sequences
    
    Parameters
    ----------
    audioTimes : list
        Times of audio codes
    audioCodes : list
        List of audio codes to match
    mwTimes : list
        Times of mworks codes
    mwCodes : list
        List of mworks codes
    minMatch : int
        Minimum match length (starting at the first index)
    maxErr : int
        Maximum number of matching errors
    
    Returns
    -------
    matches : 2d list
        List of matching times where:
            matches[:,0] = audioTimes
            matches[:,1] = mwTimes
    Notes
    -----
    Repeats in the code sequence will result in offset errors
    Setting maxErr > 0 will result in offset errors
    """
    auTimes = np.array(auTimes)
    auCodes = np.array(auCodes)
    mwTimes = np.array(mwTimes)
    mwCodes = np.array(mwCodes)
    # remove all duplicate audioCodes?
    # create lookup lists for each audioCode
    codes = np.unique(mwCodes)
    lookup = {}
    for c in codes:
        lookup[c] = np.where(auCodes == c)[0]
    
    # step through mwCodes, looking for audioTimes
    auI = -1
    matches = []
    for mwI in xrange(len(mwCodes)):
        matchFound = False
        code = mwCodes[mwI]
        for aui in lookup[code][np.where(lookup[code] > auI)[0]]:
            if match_test(auCodes[aui:],mwCodes[mwI:], minMatch, maxErr) and\
                    (auCodes[aui] == mwCodes[mwI]):
                matches.append((auTimes[aui], mwTimes[mwI]))
                offset = auTimes[aui] - mwTimes[mwI]
                auI = aui
                break
        # warn that code wasn't found?
    return matches

def slow_match_codes(audioTimes, audioCodes, mwTimes, mwCodes, minMatch = 10, maxErr = 0):
    matches = []
    auI = 0
    auN = len(audioTimes)
    testSize = minMatch + maxErr + 1
    audioCodes = np.array(audioCodes)
    for mwI in xrange(len(mwCodes)):
        matchFound = False
        auT = auI
        while (not matchFound) and ((auT + testSize) <= auN):
            # print audioCodes[auT:auT+testSize], mwCodes[mwI]
            auIndices = np.where(audioCodes[auT:auT + testSize] == mwCodes[mwI])[0]
            for dI in auIndices:
                sI = auT + dI
                # print "testing:", sI, mwI
                if match_test(audioCodes[sI:],mwCodes[mwI:], minMatch, maxErr) and\
                        (audioCodes[sI] == mwCodes[mwI]):
                    matches.append((audioTimes[sI], mwTimes[mwI]))
                    offset = audioTimes[sI] - mwTimes[mwI]
                    auI = sI + 1
                    matchFound = True
                    break
            auT += 1
        if (not matchFound):
            logging.warning("MWCode %i at %i was not found" % (mwCodes[mwI], mwTimes[mwI]))
    return matches

def test_matches():
    ncodes = 100
    mwCodes = []
    lastCode = np.random.randint(1,16)
    for i in xrange(ncodes):
        r = np.random.randint(1,16)
        while r == lastCode:
            r = np.random.randint(1,16)
        mwCodes.append(r)
        lastCode = r
    # mwCodes = list(np.random.randint(1,16,ncodes))
    auCodes = copy.deepcopy(mwCodes)
    mwTimes = np.arange(0,ncodes*1000+1,1000,dtype=int)
    offset = 1000
    auTimes = list(copy.deepcopy(mwTimes + 1000))
    mwTimes = list(mwTimes)
    
    def calc_offset(matches):
        a = np.array(matches)
        return np.mean(a[:,0] - a[:,1])
    
    # test a perfect match
    matches = match_codes(auTimes, auCodes, mwTimes, mwCodes, minMatch = 1, maxErr = 0)
    assert len(matches) == ncodes, "len(matches): %s" % len(matches)
    assert calc_offset(matches) == offset, "offset: %s" % calc_offset(matches)
    
    matches = match_codes(auTimes, auCodes, mwTimes, mwCodes, minMatch = 10, maxErr = 0)
    assert len(matches) == (ncodes - 9), "len(matches): %s" % len(matches)
    assert calc_offset(matches) == offset, "offset: %s" % calc_offset(matches)
    
    # introduce error and retest
    errI = ncodes / 2
    auCodes.insert(errI, 16) # add 16 so there is NO repeat
    t = auTimes[errI] + offset/2
    auTimes.insert(errI, t)
    
    matches = match_codes(auTimes, auCodes, mwTimes, mwCodes, minMatch = 10, maxErr = 0)
    # sometimes a deletion can result in a repeat, which causes an extra match
    # [1, 2, 3] -> after insert [1, 2, 3, 3] still matches with length 3
    # [1, 2, 3] -> after insert [1, 2, 4, 3] does not match at length 3
    # assert (len(matches) - (ncodes - (9*2))) < 2, "len(matches): %s" % len(matches)
    assert len(matches) == (ncodes - (9*2)), "len(matches): %s" % len(matches)
    # repeats can result in offset errors
    assert calc_offset(matches) == offset, "offset: %s" % calc_offset(matches)
    
    matches = match_codes(auTimes, auCodes, mwTimes, mwCodes, minMatch = 10, maxErr = 1)
    assert len(matches) == (ncodes - 9), "len(matches): %s" % len(matches)
    assert calc_offset(matches) == offset, "offset: %s" % calc_offset(matches)
    
    # remove error
    auCodes.pop(errI)
    auTimes.pop(errI)
    # remove 1 good code and retest
    while(auCodes[errI-1] == auCodes[errI+1]):
        errI += 1 # do NOT create a repeat
    auCodes.pop(errI)
    auTimes.pop(errI)
    
    matches = match_codes(auTimes, auCodes, mwTimes, mwCodes, minMatch = 10, maxErr = 0)
    assert len(matches) == (ncodes - (9*2) - 1), "len(matches): %s" % len(matches)
    assert calc_offset(matches) == offset, "offset: %s" % calc_offset(matches)
    
    matches = match_codes(auTimes, auCodes, mwTimes, mwCodes, minMatch = 10, maxErr = 1)
    # sometimes a deletion can result in a repeat, which causes an extra match
    # [1, 2, 3] -> after insert [1, 2, 3, 3] still matches with length 3
    # [1, 2, 3] -> after insert [1, 2, 4, 3] does not match at length 3
    # assert (len(matches) - (ncodes - (10*2))) < 2, "len(matches): %s" % len(matches)
    assert abs(len(matches) - (ncodes - (10*2))) < 3, "len(matches): %s" % len(matches)
    # repeats can result in offset errors, and can maxErr > 0
    # assert calc_offset(matches) == offset, "offset: %s" % calc_offset(matches)
    
    
    # need to cull offsets and/or remove outlier offsets
    
    return matches

def parse(audioFiles, threshold = 0.03, refractory = 44, minCodeTime = 441,
                    pcY = -28, pcHeight = 8.5, screenHeight = 64.54842055808264, sepRatio = 0.2):
    """
    Parse pixel clock from audio files
    
    Parameters
    ----------
    audioFiles : list
        Ordered list of pixel clock audio files. First file has LSB
    threshold : float
        Threshold at which to find events (test: abs(signal) > threshold)
    refractory : int
        Number of sub-threshold points that must be encountered before resetting the trigger
    minCodeTime : int
        Minimum time (in samples) for a given code change
    pcY : float
        Vertical position of pixel clock on screen in degrees
    pcHeight : float
        Vertical size of pixel clock in degrees. This may be XScale if pixel clock is rotated
    screenHeight : float
        Vertical size of screen in degrees (may need to calculate based on width, see MWorks core)
    sepRatio : float
        Seperation ratio of pixel clock patches (see MWorks for more information)
    
    Returns
    -------
    codes : 2d array
        Array of reconstructed and offset pixel clock codes where:
            codes[:,0] = time
            codes[:,1] = code
            codes[:,2] = trigger channel
        These codes are NOT offset for latencies of the triggered channel
    offsets : list
        Offset times (in samples) for the onset of the pixel clock patch display relative
        to the top of the screen (the beginning of the screen update)
    avgSpeed : float
        Average speed of screen refresh in degrees per sample
    """
    # transitions = []
    # channels = []
    # directions = []
    # samplerate = None
    nchannels = len(audioFiles)
    events = np.transpose(np.atleast_2d([[],[],[]]))
    for (i, af) in enumerate(audioFiles):
        logging.debug("Opening %s" % af)
        f = al.Sndfile(af,'r')
        # samplerate = f.samplerate
        logging.debug("Reading %s" % af)
        s = f.read_frames(f.nframes)
        logging.debug("Processing %s" % af)
        t = find_transitions(s, threshold, refractory)
        # c = np.sign(s[t]) * i# get state of transitions: - == down
        logging.debug("Getting sign: %i %i" % (t.max(), t.argmax()))
        d = np.sign(s[t])
        logging.debug("Getting ones")
        c = np.ones(len(d)) * i
        logging.debug("Found %i transitions on channel %i" % (len(t), i))
        ap = np.transpose(np.vstack((t,c,d)))
        events = np.vstack((events,ap)).astype(int)
        # t = refine_crossing(s, t)
        # transitions.append(t)
        # channels.append(c)
        # directions.append(d)
        # cleanup
        f.close()
        del s, t
    
    logging.debug("Reconstructing codes")
    codes, offsets, speed = reconstruct_codes(events, nchannels, minCodeTime, pcY, pcHeight, screenHeight, sepRatio)
    return codes, offsets, speed

def test_parse():
    # TODO : how do I deal with external data files?
    # audioFiles = ["pixel_clock/pixel_clock%i#01.wav" % i for i in xrange(1,5)]
    audioFiles = ["pixel_clock/%i.wav" % i for i in xrange(1,5)]
    codes, offsets, speed = parse(audioFiles)
    print offsets, speed
    # return codes, offsets, speed
    np.savetxt('codes',codes)
    print codes[:,0]
    print codes[:,1]

def old_time_match_mw_with_pc(pc_codes, pc_times, mw_codes, mw_times,
                                submatch_size = 10, slack = 0, max_slack=10,
                                mw_check_stride = 1, pc_file_offset= 0):

    time_matches = []

    for mw_start_index in range(0, len(mw_codes)-submatch_size, mw_check_stride):
        match_sequence = mw_codes[mw_start_index:mw_start_index+submatch_size]

        mw_time = mw_times[mw_start_index]

        for i in range(0, len(pc_codes) - submatch_size - max_slack):
            good_flag = True

            total_slack = 0
            for j in xrange(submatch_size):
                target = match_sequence[j]
                if target != pc_codes[i+j+total_slack]:
                    slack_match = False
                    slack_count = 0
                    while slack_count < slack and j != 0:
                        slack_count += 1
                        total_slack += 1
                        if target == pc_codes[i+j+total_slack]:
                            slack_match = True
                            break

                    if total_slack > max_slack:
                        good_flag = False
                        break

                    if not slack_match:
                        good_flag = False
                        break

            if good_flag:
                logging.info("Total slack: %d" % total_slack)
                logging.info("%s matched to %s" % \
                    (match_sequence, pc_codes[i:i+submatch_size+total_slack]))
                time_matches.append((pc_times[i], mw_time))
                break

    return time_matches

def get_events(eventsFilename):
    
    times, values = h5.events.get_events(eventsFilename, '#stimDisplayUpdate')
    mwC = []
    mwT = []
    for (t,v) in zip(times,values):
        if v is None: logging.warning("Found #stimDisplayUpdate with value = None at %f" % t)
        for i in v:
            if 'bit_code' in i.keys():
                mwC.append(int(i['bit_code']))
                mwT.append(t)
    return mwT, mwC

def test_get_events():
    # TODO
    assert False
    pass

def process(audioFiles, mwTimes, mwCodes, threshold = 0.03, refractory = 44, minCodeTime = 441,
                    pcY = -28, pcHeight = 8.5, screenHeight = 64.54842055808264, sepRatio = 0.2,
                    minMatch = 10, maxErr = 0):
    """
    Process pixel clock audio files and match codes to given MWorks codes
    
    Parameters
    ----------
    audioFiles : list
        Ordered list of pixel clock audio files. First file has LSB
    mwTimes : 1d array
        List of times (in seconds) for pixel clock code changes in MWorks in seconds
    mwCodes : 1d array
        List of pixel clock code changes as seen from MWorks
    threshold : float
        Threshold at which to find events (test: abs(signal) > threshold)
    refractory : int
        Number of sub-threshold points that must be encountered before resetting the trigger
    minCodeTime : int
        Minimum time (in samples) for a given code change
    pcY : float
        Vertical position of pixel clock on screen in degrees
    pcHeight : float
        Vertical size of pixel clock in degrees. This may be XScale if pixel clock is rotated
    screenHeight : float
        Vertical size of screen in degrees (may need to calculate based on width, see MWorks core)
    sepRatio : float
        Seperation ratio of pixel clock patches (see MWorks for more information)
    
    Returns
    -------
    matches : 2d array
        Array of matching audio and mworks times (in seconds) where:
            matches[:,0] = audio times
            matches[:,1] = mworks times
    avgSpeed : float
        Average speed of screen refresh in degrees per sample
    """
    codes, offsets, speed = parse(audioFiles, threshold, refractory, minCodeTime, pcY, pcHeight, screenHeight, sepRatio)
    auTimes = codes[:,0]
    auCodes = codes[:,1]
    matches = match_codes(auTimes, auCodes, mwTimes, mwCodes, minMatch, maxErr)
    return matches, speed

def test_process():
    # TODO : how do I deal with external data files?
    audioFiles = ["pixel_clock/pixel_clock%i#01.wav" % i for i in xrange(1,5)]
    # audioFiles = ["pixel_clock/%i.wav" % i for i in xrange(1,5)]
    codes, offsets, speed = parse(audioFiles)
    # read mworks codes
    import ast
    f = tables.openFile('K4_110720_events.h5','r')
    evs = [(r['time'],r['index']) for r in f.root.K4_110720.events.where('code == 7')]
    evs = np.array(evs)
    vs = f.root.K4_110720.values[evs[:,1]]
    f.close()
    mwC = []
    mwT = []
    for (e,v) in zip(evs,vs):
        l = ast.literal_eval(v)
        for i in l:
            if 'bit_code' in i.keys():
                mwC.append(int(i['bit_code']))
                mwT.append(e[0] / 1E6)
    auC = codes[:,1]
    auT = codes[:,0]/44100.
    matches = match_codes(auT, auC, mwT, mwC, 10, 0)
    
    # # timing
    # import time
    # startTime = time.time()
    # newmatches = new_match_codes(auT, auC, mwT, mwC, 10, 0)
    # time3 = time.time() - startTime
    # print "time3: %s" % time3
    # startTime = time.time()
    # # matches = match_codes(auT, auC, mwT, mwC, 10, 0)
    # matches = []
    # time1 = time.time() - startTime
    # startTime = time.time()
    # oldmatches = time_match_mw_with_pc(auC, auT, mwC, mwT)
    #                                 # submatch_size = 10, slack = 0, max_slack=10,
    #                                 # mw_check_stride = 1, pc_file_offset= 0):
    # time2 = time.time() - startTime
    # print "Times"
    # print "OT1: %s" % time1 #760 seconds
    # print "NT2: %s" % time2 #154 seconds
    # print "NT3: %s" % time3 #
    # 
    # nm = np.array(newmatches)
    # om = np.array(oldmatches)
    # nof = nm[:,0] - nm[:,1]
    # oof = om[:,0] - om[:,1]
    # import pylab
    # pylab.plot(nof)
    # pylab.plot(oof)
    # pylab.show()
    # 
    # return codes[:,0], codes[:,1], mwT, mwC, matches, oldmatches, newmatches

def process_from_config(config):
    """
    Parameters
    ----------
    config : cfg.Config instance
    
    Returns
    -------
    matches : 2d array
        Array of matching audio and mworks times (in seconds) where:
            matches[:,0] = audio times
            matches[:,1] = mworks times
    avgSpeed : float
        Average speed of screen refresh in degrees per sample
    """
    # get audio files
    audioDir = config.get('session','dir') + '/Audio Files'
    pcFiles, pcChannels = utils.regex_glob(audioDir, config.get('pixel clock', 'regex'))
    pcChannels = [int(ch) for ch in pcChannels]
    # sort to make sure they are ordered channel 0 -> higher
    pcFiles = np.array(pcFiles)[np.argsort(pcChannels)]
    
    # read mworks stuff
    eventsFilename = config.get('session','dir') + '/' + config.get('session','name') + '.h5'
    mwT, mwC = get_events(eventsFilename)
    
    threshold = config.getfloat('pixel clock', 'threshold')
    refractory = config.getint('pixel clock', 'refractory')
    minCodeTime = config.getint('pixel clock', 'mincodetime')
    pcY = config.getfloat('pixel clock', 'y')
    pcHeight = config.getfloat('pixel clock', 'height')
    screenHeight = config.getfloat('pixel clock', 'screenh')
    sepRatio = config.getfloat('pixel clock', 'sepratio')
    minMatch = config.getint('pixel clock', 'minmatch')
    maxErr = config.getint('pixel clock', 'maxerr')
    
    return process(pcFiles, mwT, mwC, threshold, refractory, minCodeTime,\
                pcY, pcHeight, screenHeight, sepRatio, minMatch, maxErr)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    test_threshold_crossings()
    test_state_to_code()
    test_events_to_codes()
    test_matches()
    test_parse()
    test_process()
