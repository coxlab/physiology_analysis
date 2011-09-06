#!/usr/bin/env python

import numpy as np
import pylab as pl

def plot(eventTimes, spikeTimes, preT = -0.2, postT = 0.5, nbins = 8, color = '0.5', weighted = True):
    allspikes = []
    for et in eventTimes:
        # find spiketimes that match
        spikes = spikeTimes[(spikeTimes > (et + preT)) & (spikeTimes < (et + postT))] - et
        # if len(spikes):
        #     pl.hist(spikes,bins=np.linspace(preT,postT,nbins))
        if len(spikes):
            allspikes.append(spikes)
    
    if len(allspikes) == 0: return
    
    allspikes = np.hstack(allspikes)
    if weighted:
        dt = (postT - preT) / float(nbins)
        weights = (np.ones_like(allspikes) / float(len(eventTimes))) / dt
    pl.hist(allspikes, bins = np.linspace(preT,postT,nbins+1), weights = weight)
    pl.xlim(preT, postT)

def plot_psth(event_locked, **kwargs):

    time_range = kwargs.get("time_range", (-0.100, 0.500))
    n_bins = kwargs.get("n_bins", 25)
    bin_color = kwargs.get("bin_color", '0.5')

    n_events = len(event_locked)
    #print("Plotting %d events" % (n_events))

    #plt.figure()
    plt.hold(True)
    plt.axvline(0.0, zorder=-500)#alpha=0.5)

    ts = []
    for i in range(0, n_events):
        y = (n_events - i)
        evt = event_locked[i]

        for t in evt:
            ts.append(t)

    if len(ts) != 0:
        plt.hist(ts,bins=plt.linspace(time_range[0],time_range[1],n_bins),color=bin_color,zorder=-500) # bin into 24 bins

    plt.xlim(time_range)
    #plt.show()