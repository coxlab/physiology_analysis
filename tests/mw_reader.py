#!/usr/bin/env python

import logging

logging.basicConfig(level=logging.DEBUG)

import sys
sys.path.append('../')

from physio import mw_utils

if mw_utils.MWEnabled == False:
    logging.error("mworks.data module did not import correctly, MWK reading is disabled")

# these should be corresponding mwk and h5 files
mwkFile = '/Users/graham/Repositories/coxlab/physiology_analysis/data/K4_110523/K4_110523.mwk'
h5File = '/Users/graham/Repositories/coxlab/physiology_analysis/data/K4_110523/K4_110523.h5'
eventNames = ['success',]

logging.debug("Loading mwk file: %s" % mwkFile)
mwr = mw_utils.make_reader(mwkFile)
mwr.open()
logging.debug("  getting events: %s" % str(eventNames))
mwe = mwr.get_events(eventNames)

logging.debug("Loading h5 file: %s" % h5File)
h5r = mw_utils.make_reader(h5File)
h5r.open()
logging.debug("  getting events: %s" % str(eventNames))
h5e = h5r.get_events(eventNames)

if mwe == h5e:
    print "woohoo"

def test_equal(e1, e2):
    return ((e1.time == e2.time) & (e1.value == e2.value) & (e1.time == e2.time))

def event_to_str(e):
    return "t:%i:c:%i:v:%s" (e.time, e.code, str(e.value))

for (m, h) in zip(mwe, h5e):
    if not test_equal(m,h):
        logging.error("Events %s and %s did not equal" % (event_to_str(m), event_to_str(h)))

print mwe

print h5e