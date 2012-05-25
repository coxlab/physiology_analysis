#!/usr/bin/env python

import numpy as np
import pylab as pl


def plot(eventTimes, spikeTimes, preT=-0.2, postT=0.5, marker=',k'):
    for (y, et) in enumerate(eventTimes):
        # find spiketimes that match
        spikes = spikeTimes[(spikeTimes > (et + preT)) & \
                (spikeTimes < (et + postT))] - et
        if len(spikes):
            pl.plot(spikes, np.ones_like(spikes) * y, marker, hold=True)
    pl.xlim(preT, postT)


def plot_rasters(event_locked, **kwargs):

    v_spacing = kwargs.get("vertical_spacing", 0.05)
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
            plt.plot( t, y, '|k')
            ts.append(t)

    if len(ts) != 0:
        plt.hist(ts,bins=plt.linspace(time_range[0],time_range[1],n_bins),color=bin_color,zorder=-500) # bin into 24 bins

    plt.xlim(time_range)
    #plt.show()
