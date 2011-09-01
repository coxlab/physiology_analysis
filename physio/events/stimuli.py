#!/usr/bin/env python

import logging

import numpy as np
import tables

from .. import utils
from .. import h5

def get_stimuli(eventsFile, timeRange = None):
    times, values = h5.events.get_events('#stimDisplayUpdate', timeRange)
    
    stimTimes = []
    stims = []
    for (t, v) in zip(times, values):
        if v is None: logging.warning("Found #stimDisplayUpdate with value = None at %f" % t)
        for i in v:
            if 'image' in i.keys(): # skips bit_code and blueSquare
                stimTimes.append(t)
                stims.append(i)
    return stimsTimes, stims

def match(stimTimes, stims, matchDict):
    matchedTimes = []
    matchedStims = []
    for (t,s) in zip(stimTimes, stims):
        if all([(matchDict[k] == s[k]) for k in matchDict.keys()]):
            matchedTimes.append(t)
            matchedStims.append(s)
    return matchedTimes, matchedStims

def stimhash(stim):
    return "%s_%.3f_%.3f_%.3f_%.3f_%.3f" % (stim['name'], stim['pos_x'], stim['pos_y'], stim['rotation'], stim['size_x'], stim['size_y'])

def unhash(stimhash):
    tokens = stimhash.split('_')
    assert len(tokens) == 6, "Invalid stimulus hash[%s] contained != 6 tokens[%i]" % (stimhash, len(tokens))
    stim = {}
    stim['name'] = tokens[0]
    for (name, token) in zip(['pos_x','pos_y','rotation','stim_x','stim_y'], tokens[1:]):
        stim[name] = float(token)
    return stim

def count(stims):
    counts = {}
    for s in stims:
        h = stimhash(s)
        counts[h] = counts.get(h,0) + 1
    return counts

def unique(stims):
    return [unhash(k) for k in count(stims).keys()] # keys are stimhashes
