#!/usr/bin/env python

import logging, tempfile

logging.basicConfig(level=logging.DEBUG)

import numpy as np

import sys
sys.path.append('../')

from physio.pixel_clock import TimeBase
from physio.utils import read_epochs_audio, read_epochs_mw


# make temporary test directory
tmpdir = tempfile.mkdtemp('./')

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
time_base = TimeBase(matches)

# try to read in epochs that do not exists
e = read_epochs_audio(tmpdir)
assert(len(e)==0)

e = read_epochs_mw(tmpdir, time_base)
assert(len(e)==0)

# make fake epoch file (in audio units)
epochs = np.array([[1.,4.], [5.,10.]])
np.savetxt(tmpdir+'/epochs', epochs)

e = read_epochs_audio(tmpdir)
logging.debug("Should have read epochs: %s" % str(epochs))
logging.debug("  Actually read epochs : %s" % str(e))
err = sum(sum(epochs - e))
logging.debug("  Error: %f" % err)
if err > 1E-6:
    logging.error("Epoch read audio error too large: %f" % err)

e = read_epochs_mw(tmpdir, time_base)
ufunc_audio_to_mw = np.frompyfunc(time_base.audio_time_to_mw, 1, 1)
mw_epochs = ufunc_audio_to_mw(epochs)
logging.debug("Should have read epochs: %s" % str(mw_epochs))
logging.debug("  Actually read epochs : %s" % str(e))
err = sum(sum(mw_epochs - e))
logging.debug("  Error: %f" % err)
if err > 1E-6:
    logging.error("Epoch read mworks error too large: %f" % err)