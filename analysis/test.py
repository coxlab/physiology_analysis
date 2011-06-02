#!/usr/bin/env python

import sys

import pixel_clock

baseDir =  '/Users/graham/Repositories/coxlab/physiology_analysis/data/K4_110523'
mwTimeOffset = 1358.6488178654547 # mw time at audio time 0
epochTime_mw = (2075.8280759999998, 5771.5493690000003) # mw time of starting and ending event for recording epoch


# convert epoch time to audio units
epochTime_audio = (epochTime_mw[0] - mwTimeOffset, epochTime_mw[1] - mwTimeOffset)

# get spikes for epoch
caton_cluster_data(baseDir, 1, time_range=epochTime_audio)