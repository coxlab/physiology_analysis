#!/usr/bin/env python

import logging, optparse, os, sys
logging.basicConfig(level = logging.DEBUG)
#import matplotlib
import numpy as np
import pylab as pl

import physio

snrw = (30,70)
sessionName = 'L2_110927'
epochNumber = 0

rms = lambda x: pl.sqrt(pl.sum(x ** 2.) / len(x))
snr = lambda x: (rms(x[snrw[0]:snrw[1]])/rms(x[:snrw[0]]))**2

config = physio.cfg.load(sessionName)

session = physio.session.load(sessionName, epochNumber)

#ncells = session.get_n_cells()
snrms = []
snrss = []
snrns = []
cells = []
for ch in xrange(1,33):
    for cl in xrange(session.get_n_clusters(ch)):
        waves = session.get_spike_waveforms(ch, cl)
        snrs = pl.array([snr(w) for w in waves])
        snrms.append(pl.mean(snrs))
        snrss.append(pl.std(snrs))
        snrns.append(len(snrs))
        cells.append([ch,cl])
        logging.debug("Cell %i [ch:%02i,cl:%02i]: SNR %.4f +- %.4f" % (len(cells)-1, ch, cl, snrms[-1], snrss[-1] / pl.sqrt(snrns[-1])))
