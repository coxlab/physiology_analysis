#!/usr/bin/env python

import numpy as np

from .. import peaks

def test_threshold_crossings():
    t = np.linspace(0., 10., 101)
    f = 0.5
    x = np.sin(t * f * 2 * np.pi)
    p = np.where(x > 0, x, np.zeros_like(x))
    n = np.where(x < 0, x, np.zeros_like(x))
    a = np.abs(x)
    i = -a
    
    gi = peaks.find_negative_threshold_crossings(x, -0.3, 3)
    assert all(gi == [11,31,51,71,91])
    
    gi = peaks.find_positive_threshold_crossings(x, 0.3, 3)
    assert all(gi == [1,21,41,61,81])
    
    gi = peaks.find_both_threshold_crossings(x, 0.3, 2)
    assert gi[0] == 1
    
    gi = peaks.find_both_threshold_crossings(x, 0.3, 1)
    assert all(gi == [1, 11, 21, 31, 41, 51, 61, 71, 81, 91])
    
    # refine crossing
    gi = peaks.find_both_threshold_crossings(a, 0.3, 1)
    rt = peaks.refine_crossings(a, gi)
    assert all(rt == [ 0, 10, 20, 30, 40, 50, 60, 70, 80, 90])
    
    gi = peaks.find_both_threshold_crossings(i, 0.3, 1)
    rt = peaks.refine_crossings(i, gi)
    assert all(rt == [ 0, 10, 20, 30, 40, 50, 60, 70, 80, 90])
    return True
