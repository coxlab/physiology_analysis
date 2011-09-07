#!/usr/bin/env python

import numpy as np

def find_negative_threshold_crossings(signal, threshold, refractory):
    """
    Find points that are less than a negative threshold value
    
    Parameters
    ----------
    signal : 1d array
        Signal in which to find threshold crossings
    threshold : float
        Threshold at which to find crossings (test: signal < threshold)
    refractory : int
        Number of sub-threshold points that must be encountered before resetting the trigger
    
    Returns
    -------
    crossings : 1d array
        Indicies where the signal crosses the threshold
    """
    
    assert threshold <= 0, "Threshold [%f] must be negative" % threshold
    assert type(signal) == np.ndarray, "Signal must be a ndarray not %s" % type(signal)
    assert signal.ndim == 1, "Signal must be 1d not %i" % signal.ndim
    assert refractory >= 0, "Refractory[%i] must >= 0" % refractory
    
    st = np.where(signal < threshold)[0]
    if len(st) < 2:
        return st
    ds = np.where(np.diff(st) > refractory)[0]
    gi = np.hstack((st[0],st[ds+1]))
    return gi

def find_positive_threshold_crossings(signal, threshold, refractory):
    """
    Find points that are greater than a positive threshold value
    
    Parameters
    ----------
    signal : 1d array
        Signal in which to find threshold crossings
    threshold : float
        Threshold at which to find crossings (test: signal > threshold)
    refractory : int
        Number of sub-threshold points that must be encountered before resetting the trigger
    
    Returns
    -------
    crossings : 1d array
        Indicies where the signal crosses the threshold
    """
    
    assert threshold >= 0, "Threshold [%f] should be positive" % threshold
    assert type(signal) == np.ndarray, "Signal must be a ndarray not %s" % type(signal)
    assert signal.ndim == 1, "Signal must be 1d not %i" % signal.ndim
    assert refractory >= 0, "Refractory[%i] must >= 0" % refractory
    
    st = np.where(signal > threshold)[0]
    if len(st) < 2:
        return st
    ds = np.where(np.diff(st) > refractory)[0]
    gi = np.hstack((st[0],st[ds+1]))
    return gi

def find_both_threshold_crossings(signal, threshold, refractory):
    """
    Find points that are more extreme than a threshold value
    
    Parameters
    ----------
    signal : 1d array
        Signal in which to find threshold crossings
    threshold : float
        Threshold at which to find crossings (test: abs(signal) > threshold)
    refractory : int
        Number of sub-threshold points that must be encountered before resetting the trigger
    
    Returns
    -------
    crossings : 1d array
        Indicies where the signal crosses the threshold
    """
    
    assert threshold >= 0, "Threshold [%f] should be positive" % threshold
    assert type(signal) == np.ndarray, "Signal must be a ndarray not %s" % type(signal)
    assert signal.ndim == 1, "Signal must be 1d not %i" % signal.ndim
    assert refractory >= 0, "Refractory[%i] must >= 0" % refractory
    
    stp = np.where(signal > threshold)[0]
    stn = np.where(signal < -threshold)[0]
    st = np.union1d(stp,stn)
    if len(st) < 2:
        return st
    ds = np.where(np.diff(st) > refractory)[0]
    gi = np.hstack((st[0], st[ds+1]))
    return gi 

def refine_crossings(signal, crossings):
    """
    Refine the threshold crossings by looking back in time for the first contiguous interval
    that moved the signal in the same direction as the threshold crossing
    
    Parameters
    ----------
    signal : 1d array
        Signal in which to find threshold crossings
    crossings : 1d array
        Indicies where the signal crosses the threshold
    
    Returns
    -------
    refined : 1d array
        Indicies where the signal began its rise/fall to a threshold crossing
    
    Notes
    -----
    For a rectified sine wave (abs(sin)) with threshold at 0.5, the threshold
    crossings will be at halfway up each 'bump'. The refined crossings will be
    at the valleys between bumps.
    """
    refined = np.empty_like(crossings)
    for i in xrange(len(crossings)):
        transition = crossings[i]
        if transition == 0: continue
        
        crossing = signal[transition]
        delta = signal[transition] - signal[transition-1]
        while (transition > 0) and \
            (np.sign(signal[transition] - signal[transition-1]) == np.sign(crossing)):
            transition -= 1
        refined[i] = transition
    return refined