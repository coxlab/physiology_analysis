#!/usr/bin/python

import numpy


def find_isolation_start_by_isi(spike_times, threshold=3, chunk_size=100):
    """
    Poor isolation (during the beginning part of the session) results in
    high isis. So to find the start of the isolated period

    1) calculate spike isis
    2) break up all isis into chunks (size = chunk_size)
    3) find the maximum isi for each chunk
    4) find the mean and std of the maximum isi for each chunk
    5) find the earliest chunk with an isi < mean + std * threshold
    6) return the time at the starting point of that chunk
    """
    if len(spike_times) < (chunk_size * 10 + 1):
        return spike_times[0]
    isi = spike_times[1:] - spike_times[:-1]
    nc = len(isi) / chunk_size
    misi = []
    for i in xrange(nc - 1):
        misi.append(isi[i * 100:(i + 1) * 100].max())
    h = len(misi) / 2
    m = numpy.mean(misi[h:])
    s = numpy.mean(misi[h:])
    gi = numpy.where(misi < (m + s * threshold))[0]
    if len(gi) == 0:
        return spike_times[0]
    ci = gi.min() * chunk_size + 1
    if ci >= len(spike_times):
        return spike_times[-1]
    return spike_times[ci]
