#!/usr/bin/env python

import shlex, subprocess

import pylab as pl

import scikits.audiolab as al

freqs = [1,1000] # hz
sf = 44100
cf = 200
t = pl.arange(sf * 2) / float(sf)
orig = pl.zeros(t.shape)
for f in freqs:
    orig += pl.sin(2. * pl.pi * f * t) / float(len(freqs))
# orig[int(sf * 0.01)] = 1.

al.wavwrite(orig,'orig.wav',sf)
taps = int(sf * 1/float(cf) * 4.)
cmd = 'sox orig.wav filt.wav sinc -M -n %i %i' % (taps, cf)
print cmd
subprocess.check_call(shlex.split(cmd))

filt = al.wavread('filt.wav')[0]

pl.subplot(221)
pl.plot(t,orig)
pl.xlim((0,0.02))
pl.ylim((-1,1))
pl.subplot(222)
pl.psd(orig,NFFT=1024,Fs=sf)
pl.xlim((0,2000))
pl.ylim((-160,-20))

pl.subplot(223)
pl.plot(t,filt)
pl.xlim((0,0.02))
pl.ylim((-1,1))
pl.subplot(224)
pl.psd(filt,NFFT=1024,Fs=sf)
pl.xlim((0,2000))
pl.ylim((-160,-20))

pl.show()