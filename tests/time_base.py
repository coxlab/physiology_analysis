#!/usr/bin/env python

import numpy as np

import sys
sys.path.append('../')

from physio.pixel_clock import TimeBase

# construct fake data for a TimeBase object
mwStart = 1303
audioStart = 0
audioOffset = 10.
drift = 100./ (1E6) # 100 part per million drift
interval = 0.1 # events occur ever 0.1 seconds
matches = []
for i in xrange(1000):
    t = i * interval
    mwT = t + mwStart
    auT = t + audioStart + t * drift
    matches.append((auT,mwT))

# print matches

t = TimeBase(matches)

print "MWStart : %f" % mwStart
auMatch = t.mw_time_to_audio(mwStart)
print " in audio : %f" % auMatch
print " should be : %f" % audioStart
print " error : %f" % (auMatch - audioStart)

print

print "Audio : %f" % audioStart
mwMatch = t.audio_time_to_mw(audioStart)
print " in mw : %f" % mwMatch
print " should be : %f" % mwStart
print " error : %f" % (mwMatch - mwStart)
    