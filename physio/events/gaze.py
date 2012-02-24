#!/usr/bin/env python

import logging
import sys

import numpy as np
import pylab as pl


def get_and_unpack(mwkf, code, start=0):
    evs = mwkf.get_events(codes=[code, ])
    t = np.array([e.time for e in evs[start:]])
    v = np.array([e.value for e in evs[start:]])
    return t, v


def calc_velocity(t, v):
    vel = (v[1:] - v[:-1]) / (t[1:] - t[:-1])
    return vel


def find_good_by_deviation(h, v, thresh=30):
    """
    Find indices of data points that do not deviate more than thresh
    """
    hm = np.mean(h)
    logging.debug("Horizontal mean: %f" % hm)
    vm = np.mean(v)
    logging.debug("Vertical mean: %f" % vm)

    hgood = np.where(abs(h - hm) < thresh)[0]
    vgood = np.where(abs(v - vm) < thresh)[0]

    good = np.intersect1d(hgood, vgood)
    return good


def clean_by_deviation(tt, t, h, v, thresh=30):
    hm = np.mean(h)
    logging.debug("Horizontal mean: %f" % hm)
    vm = np.mean(v)
    logging.debug("Vertical mean: %f" % vm)

    hgood = np.where(abs(h - hm) < thresh)[0]
    vgood = np.where(abs(v - vm) < thresh)[0]

    good = np.intersect1d(hgood, vgood)

    return tt[good], t[good], h[good], v[good]


def clean_by_difference(tt, t, h, v, thresh=30):
    dh = h[1:] - h[:-1]
    dv = v[1:] - v[:-1]

    hgood = np.where(abs(dh) < thresh)[0]
    vgood = np.where(abs(dv) < thresh)[0]

    good = np.intersect1d(hgood, vgood)

    return tt[good], t[good], h[good], v[good]


def clean_by_velocity(tt, t, h, v, thresh=1000):
    hvel = calc_velocity(t, h)
    vvel = calc_velocity(t, v)

    # hgood = np.where(abs(hvel) < thresh)[0]
    # vgood = np.where(abs(vvel) < thresh)[0]

    hbad = np.where(abs(hvel) > thresh)[0]
    vbad = np.where(abs(vvel) > thresh)[0]

    bad = np.union1d(hbad, vbad) + 1
    # bad = np.union1d(bad, bad+1)

    return np.delete(tt, bad), np.delete(t, bad), \
            np.delete(h, bad), np.delete(v, bad)


def clean_by_acceleration(tt, t, h, v, thresh=1000):
    hvel = calc_velocity(t, h)
    vvel = calc_velocity(t, v)
    hacc = calc_velocity(t[1:], hvel)
    vacc = calc_velocity(t[1:], vvel)

    # hgood = np.where(abs(hacc) < thresh)[0]
    # vgood = np.where(abs(vacc) < thresh)[0]
    #
    # good = np.intersect1d(hgood, vgood) + 2
    #
    # return tt[good], t[good], h[good], v[good]

    hbad = np.where(abs(hacc) > thresh)[0]
    vbad = np.where(abs(vacc) > thresh)[0]

    bad = np.union1d(hbad, vbad) + 1
    bad = np.union1d(bad, bad + 1)

    return np.delete(tt, bad), np.delete(t, bad), \
            np.delete(h, bad), np.delete(v, bad)


def get_gaze(mwkf):
    # skip first event, it seems to be erroneous
    ht, hv = get_and_unpack(mwkf, 'gaze_h', 1)
    vt, vv = get_and_unpack(mwkf, 'gaze_v', 1)
    pt, pv = get_and_unpack(mwkf, 'pupil_radius', 1)
    tt, tv = get_and_unpack(mwkf, 'cobra_timestamp', 1)
    return tt, tv, hv, vv


def clean_gaze(tt, tv, hv, vv):
    return clean_by_deviation(*clean_by_acceleration(tt, tv, hv, vv))


def get_clean_gaze(mwkf):
    return clean_gaze(*get_gaze(mwkf))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    df = 'data/K4_110726.mwk'
    if len(sys.argv) > 1:
        df = sys.argv[1]

    import mworks.data
    mwkf = mworks.data.MWKFile(df)
    mwkf.open()

    tt, t, h, v = get_gaze(mwkf)
    pl.figure()
    r = (tt, t, h, v)
    pl.subplot(421)
    pl.plot(r[1], r[2])
    pl.title('Horizontal')
    pl.ylabel('Raw')
    pl.subplot(422)
    pl.plot(r[1], r[3])
    pl.title('Vertical')

    r = clean_gaze(tt, t, h, v)  # clean_by_acceleration(tt, t, h, v)
    pl.subplot(423)
    pl.plot(r[1], r[2])
    pl.ylabel('Clean')
    pl.subplot(424)
    pl.plot(r[1], r[3])
    pl.ylabel

    r = clean_by_acceleration(tt, t, h, v)
    pl.subplot(425)
    pl.plot(r[1], r[2])
    pl.ylabel('Accel')
    pl.subplot(426)
    pl.plot(r[1], r[3])

    r = clean_by_deviation(tt, t, h, v)
    pl.subplot(427)
    pl.plot(r[1], r[2])
    pl.ylabel('Dev')
    pl.subplot(428)
    pl.plot(r[1], r[3])

    # pl.subplot(211)
    # pl.plot(t,h)
    # pl.title('Horizontal')
    # pl.subplot(212)
    # pl.plot(t,v)
    # pl.title('Vertical')
    pl.figure()
    pl.hist(1 / (t[1:] - t[:-1]))
    pl.title('HZ')
    pl.show()
