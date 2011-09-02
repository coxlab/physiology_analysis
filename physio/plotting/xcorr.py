#!/usr/bin/env python

import numpy as np
import pylab as pl

def plot(spikeTimes1, spikeTimes2, margin = 0.1, **kwargs):
    if len(spikeTimes1) == 0 or len(spikeTimes2) == 0: return
    dt = np.array([spikeTimes2[np.abs(spikeTimes2 - i).argmin()] - i for i in spikeTimes1])
    if len(dt) == 0: return
    dt = dt[np.abs(dt) < margin]
    pl.hist(dt, **kwargs)
    pl.xlim(-margin,+margin)