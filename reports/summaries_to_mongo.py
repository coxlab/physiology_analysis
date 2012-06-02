#!/usr/bin/env python

import datetime
import logging
import os
import re
import sys

logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.WARNING)

import pylab
import numpy
import pymongo
import scipy.stats

from joblib import Parallel, delayed

import brainatlas
import physio

import cellsummary
import clustermerge


#blacklist_animals = ['fake', 'H3', 'H4', 'H7', 'H8']
blacklist_animals = []

min_spikes = 100
min_rate = 0.0001  # hz
rwin = (0.05, 0.2)
bwin = (-0.15, 0.0)

attrs = ['name', 'pos_x', 'pos_y', 'size_x', 'rotation']


shift_locations = True
shifts = {  # ap, dv, ml
    'H3': (0., .2, .9),  # unverified
    'H8': (0., 0., 1.),  # unverified
    'K2': (.7, 0., -6.8),  # unverified
    'K4': (0., 0., 0.),
    'L1': (.5, -.6, -1.7),
    'L2': (-.3, -1.0, -1.8),
    'M2': (0., 0., 0.),
    'M4': {
        '120106': (-.8, 0., -1.),
        '120109': (-.8, 0., -1.),
        '120111': (-.8, 0., -1.),
        '120113': (-.8, 0., -1.),
        '120118': (-.8, 0., -1.),
        '*': (0., 0., -.2),
        },
}  # add this to the locations


def find_shift(animal, date):
    shift = shifts[animal]
    if not isinstance(shift, dict):
        return shift
    if date in shift:
        return shift[date]
    return shift['*']


def get_location(summary, cell):
    locs = numpy.array([get_channel_location(summary, ch) \
            for (ch, cl) in cell])
    return tuple(numpy.mean(locs, 0))


def get_channel_location(summary, ch):
    """ ap, dv, ml """
    location = numpy.array(summary.get_location(ch).tolist())
    if shift_locations:
        shift = numpy.array(find_shift(summary.animal, summary.date))
        location = numpy.array(summary.get_location(ch).tolist())
        return tuple(location + shift)
    else:
        return tuple(location)


mongo_server = 'coxlabanalysis1.rowland.org'
mongo_db = 'physiology'
mongo_collection = 'cells_shift'


def make_mongo_safe(d, pchar=','):
    """
    Some 'inspiration' (e.g. liberal copying) from:
        https://github.com/jaberg/hyperopt/blob/master/hyperopt/base.py
        SONify
    """
    if isinstance(d, dict):
        nd = {}
        for k in d.keys():
            nk = str(k)
            nk = nk.replace('.', pchar)
            nd[nk] = make_mongo_safe(d[k])
        return nd
    elif isinstance(d, (list, tuple)):
        return type(d)([make_mongo_safe(i) for i in d])
    elif isinstance(d, numpy.ndarray):
        return make_mongo_safe(list(d))
    elif isinstance(d, numpy.bool_):
        return bool(d)
    elif isinstance(d, numpy.integer):
        return int(d)
    elif isinstance(d, numpy.floating):
        return float(d)
    return d


def write_cell(cell):
    # write cell to mongo db
    coll = pymongo.Connection(mongo_server)[mongo_db][mongo_collection]
    safe = make_mongo_safe(cell)
    coll.insert(safe)


def clear_mongo():
    db = pymongo.Connection(mongo_server)[mongo_db]
    if mongo_collection in db.collection_names():
        db.drop_collection(mongo_collection)


def calc_velocity(signal, time):
    return (signal[1:] - signal[:-1]) / (time[1:] - time[:-1])


def clean_gaze(gaze, acc_thresh=1000, dev_thresh=30):
    # acceleration
    hvel = calc_velocity(gaze['h'], gaze['cobra_timestamp'])
    vvel = calc_velocity(gaze['v'], gaze['cobra_timestamp'])
    hacc = calc_velocity(hvel, gaze['cobra_timestamp'][1:])
    vacc = calc_velocity(vvel, gaze['cobra_timestamp'][1:])

    hbad = numpy.where(abs(hacc) > acc_thresh)[0]
    vbad = numpy.where(abs(vacc) > acc_thresh)[0]

    bad = numpy.union1d(hbad, vbad) + 1
    bad = numpy.union1d(bad, bad + 1)

    gaze = numpy.delete(gaze, bad)

    # deviation
    hm = numpy.mean(gaze['h'])
    vm = numpy.mean(gaze['v'])

    bad = numpy.union1d( \
            numpy.where(abs(gaze['h'] - hm) > dev_thresh)[0],
            numpy.where(abs(gaze['v'] - vm) > dev_thresh)[0])

    gaze = numpy.delete(gaze, bad)
    return gaze


def cull_trials_by_gaze(trials, gaze, \
        std_thresh=numpy.inf, dev_thresh=5):
    median_h = numpy.median(gaze['h'])
    keep = numpy.ones(len(trials)).astype(bool)
    for (i, trial) in enumerate(trials):
        start, end = trial['time'], trial['time'] + trial['duration']
        trial_gaze = gaze[numpy.logical_and(gaze['time'] > start, \
                gaze['time'] < end)]

        trial_mean_h = numpy.mean(trial_gaze['h'])
        trial_std_h = numpy.std(trial_gaze['h'])

        if (trial_std_h > std_thresh):
            keep[i] = False
            continue

        if (abs(trial_mean_h - median_h) > dev_thresh):
            keep[i] = False
            continue
    return trials[keep]


def get_driven_rate():
    pass


def get_responsivity(spike_times, trials, bwin, rwin):
    baseline, response = physio.spikes.triallock.rate_per_trial( \
            spike_times, trials['time'], [bwin, rwin])
    return baseline, response, test_responsivity(baseline, response)


def test_responsivity(baseline, response):
    t, p = scipy.stats.ttest_rel(baseline, response)
    return {'t': t, 'p': p}


def get_selectivity(summary, trials, stims, attr):
    uniques = numpy.unique(stims[attr])
    conditions = {}
    for unique in uniques:
        ftrials = summary.filter_trials(trials, {attr: unique})
        if len(ftrials) == 0:
            continue
        conditions[unique] = ftrials['response']

    stat = test_selectivity(conditions.values())
    mv = {}
    for k, v in conditions.iteritems():
        mv[k] = numpy.mean(v)
    mv = sorted(mv.iteritems(), key=lambda i: i[1])
    sorted_keys = [i[0] for i in mv[::-1]]
    means = []
    stds = []
    ns = []
    for k in sorted_keys:
        v = conditions[k]
        ns.append(len(v))
        stds.append(numpy.std(v))
        means.append(numpy.mean(v))

    return sorted_keys, means, stds, ns, stat


def test_selectivity(responses):
    H = F = X = numpy.nan
    p = p2 = p3 = numpy.nan

    try:
        H, p = scipy.stats.kruskal(responses)
    except Exception as e:
        logging.warning("kruskal failed with: %s" % str(e))

    try:
        #F, p2 = scipy.stats.f_oneway(*all_sqrt_counts)
        F, p2 = scipy.stats.f_oneway(*responses)
        #print ("anova F=%f, p=%f" % (F, p2))
    except Exception as e:
        logging.warning("anova failed with: %s" % str(e))

    try:
        lens = [len(r) for r in responses]
        trunced = [numpy.array(r[0:numpy.min(lens)]) for r in responses]
        X, p3 = scipy.stats.friedmanchisquare(*trunced)
        #print ("friedman=%f, p=%f" % (X, p3))
    except Exception as e:
        logging.warning("friedman failed with: %s" % str(e))

    try:
        mr = [numpy.mean(r) for r in responses]
        sel_index = physio.spikes.selectivity.selectivity(mr)
    except Exception as e:
        logging.warning("selectivity failed with: %s" % str(e))

    return {'H': H, 'Hp': p, 'F': F, 'Fp': p2, 'X': X, 'Xp': p3, \
            'sel': sel_index}


def make_response_matrix(summary, trials, stims, attr1, attr2, key='response'):
    # M, S, N, L
    u1 = sorted(numpy.unique(stims[attr1]))
    u2 = sorted(numpy.unique(stims[attr2]))
    n1 = len(u1)
    n2 = len(u2)
    M = numpy.zeros((n1, n2))
    S = numpy.zeros((n1, n2))
    N = numpy.zeros((n1, n2))
    L = [u1, u2]
    for (i1, l1) in enumerate(u1):
        for (i2, l2) in enumerate(u2):
            ftrials = summary.filter_trials(trials, {attr1: l1, attr2: l2})
            N[i1, i2] = len(ftrials)
            if N[i1, i2] == 0:
                M[i1, i2] = numpy.nan
                S[i1, i2] = numpy.nan
            else:
                M[i1, i2] = numpy.mean(ftrials[key])
                S[i1, i2] = numpy.std(ftrials[key])
    return M, S, N, L


def get_separability(summary, trials, stims, attr1, attr2):
    M, S, N, L = make_response_matrix(summary, trials, stims, attr1, attr2)
    if M.shape[0] == 1 or M.shape[1] == 1:
        return M, S, N, L, {}
    else:
        return M, S, N, L, test_separability(M)


def test_separability(M):
    sep, spi, ps = physio.spikes.separability.\
            separability_permutation(M)
    if len(ps) == 2:
        p0 = ps[0]
        p1 = ps[1]
    else:
        p0 = p1 = None
    return {'sep': sep, 'spi': spi, 'p0': p0, 'p1': p1}


def stim_to_dict(stim):
    return dict([(k, stim[k]) for k in dict(stim.dtype.fields).keys()])


def get_tolerance(summary, trials, stims):
    conditions = {}
    stimds = {}
    for stim in stims:
        sd = stim_to_dict(stim)
        sis = summary.get_stimulus_indices(sd)
        assert len(sis) == 1, "Found %s stim that matched %s" % (len(sis), sd)
        si = sis[0]
        if si in conditions:
            raise ValueError("Two stimuli matched[%s]: %s" % (si, sd))
        ftrials = summary.filter_trials_by_stim_index(trials, si)
        if len(ftrials) == 0:
            continue
        conditions[si] = ftrials['response']
        stimds[si] = sd

    stat = test_selectivity(conditions.values())
    mv = {}
    for k, v in conditions.iteritems():
        mv[k] = numpy.mean(v)
    mv = sorted(mv.iteritems(), key=lambda i: i[1])
    sorted_keys = [i[0] for i in mv[::-1]]
    means = []
    stds = []
    ns = []
    for k in sorted_keys:
        v = conditions[k]
        ns.append(len(v))
        stds.append(numpy.std(v))
        means.append(numpy.mean(v))

    return sorted_keys, means, stds, ns, stat, stimds


def get_friedman(summary, trials, stims):
    ids = numpy.unique(stims['name'])
    trans = numpy.unique(stims[list(stims.dtype.names[1:])])
    M = numpy.zeros((len(ids), len(trans), 5))
    for (ni, n) in enumerate(ids):
        for (ti, t) in enumerate(trans):
            sd = dict(name=n)
            sd.update(dict(zip(trans.dtype.names, t)))
            ft = summary.filter_trials(trials, sd)
            if len(ft) == 0:
                raise ValueError("0 Trials with %s [%s]" % (n, t))
            #br = numpy.mean(ft['baseline'])
            M[ni, ti, 0] = numpy.mean(ft['response'])
            M[ni, ti, 1] = numpy.std(ft['response'])
            M[ni, ti, 2] = len(ft['response'])
            M[ni, ti, 3] = numpy.mean(ft['baseline'])
            M[ni, ti, 4] = numpy.std(ft['baseline'])
    r = M[:, :, 0] - M[:, :, 3]  # use driven response for now
    Q, p = scipy.stats.friedmanchisquare(*r)  # stat = Q, p
    trans = [list(t) for t in trans]  # make mongo happy
    return M, ids, trans, {'Q': Q, 'p': p}


global sections
sections = {}


def get_closest_section(ap):
    bounds = brainatlas.section.bounds
    index = -1
    for i in sorted(bounds.keys()):
        ref_ap = bounds[i]
        if ref_ap < ap:
            break
        index = i
    global sections
    if index in sections:
        return sections[index]
    else:
        areas = 'V2L AuD Au1 AuV PRh V1B V1M TeA Ect'.split()
        sections[index] = brainatlas.section.Section(index, areas=areas)
        return sections[index]


def get_area(location):
    ap, dv, ml = location
    # flip dv as brainatlas expects + to be down
    dv *= -1
    #areas = 'V2L AuD Au1 AuV PRh V1B V1M TeA Ect'.split()
    cs = get_closest_section(ap)
    #cs = brainatlas.section.get_closest_section(ap, areas=areas)
    area = cs.get_area_for_location(ml, dv, 'skull')
    assert len(area) == 1, "len(area) != 1: %s" % area
    return str(area[0])


# have this dump directly to mongo (remove plotting)
def process_summary(summary_filename, overrides):
    summary = cellsummary.CellSummary(summary_filename, overrides)
    logging.debug("Processing %s" % summary._filename)

    animal = summary.animal
    date = summary.date
    # convert to datetime
    dt = datetime.datetime(int('20' + date[:2]), int(date[2:4]), int(date[4:]))

    # cull trials by success
    trials = summary.get_trials()
    if len(trials) == 0:
        logging.error("No trails for %s" % summary._filename)
        return
    trials = trials[trials['outcome'] == 0]

    # and gaze
    try:
        gaze = clean_gaze(summary.get_gaze())
    except Exception as E:
        logging.warning("Fetching gaze failed: %s" % E)
        gaze = []

    nt = len(trials)
    if len(gaze) > 0:
        logging.debug("N Trials before gaze culling: %i" % len(trials))
        trials = cull_trials_by_gaze(trials, gaze)
        logging.debug("N Trials after gaze culling: %i" % len(trials))
    n_culled_trials = nt - len(trials)

    for cid in summary.cells():
        # cid is a list of ch/cl tuples
        # hack for ch, cl
        ch, cl = cid[0]
        scid = ' '.join(['%i.%i' % t for t in cid])
        ctrials = trials.copy()
        cell = {}
        cell['err'] = ""
        # things to fix for cluster merging
        # channel : see below
        # cluster : just call this cell_index
        # get_spike_times : merge them in summary.get_spike_times
        # get_spike_snrs : merge them in summary.get_spike_snrs
        # get_location : average channel locations?
        cell['ch'] = ch  # FIXME
        cell['cl'] = cl  # FIXME
        cell['cid'] = scid
        cell['animal'] = animal
        cell['date'] = date
        cell['datetime'] = dt

        logging.debug("ch: %i, cl: %i" % (ch, cl))
        # rate
        spike_times = numpy.array([])
        for ch, cl in cell:
            spike_times = numpy.hstack((spike_times, \
                    summary.get_spike_times(ch, cl)))
            #spike_times = summary.get_spike_times(ch, cl)  # FIXME

        trange = (spike_times.min(), spike_times.max())
        cell['raw_trange'] = trange

        # trange = summary.get_epoch_range()
        # find start of isolation
        isolation_start = physio.spikes.times.\
                find_isolation_start_by_isi(spike_times)

        spike_times = spike_times[spike_times >= isolation_start]

        nspikes = len(spike_times)
        cell['nspikes'] = nspikes

        trange = (spike_times.min(), spike_times.max())
        rate = nspikes / (trange[1] - trange[0])
        cell['rate'] = rate
        cell['trange'] = trange

        # snr
        try:
            snrs = numpy.array([])
            for ch, cl in cell:
                snrs = numpy.hstack((snrs, \
                        summary.get_spike_snrs(ch, cl, timeRange=trange)))
            #snrs = summary.get_spike_snrs(ch, cl, timeRange=trange)  # FIXME
            cell['snr_mean'] = numpy.mean(snrs)
            cell['snr_std'] = numpy.std(snrs)
        except Exception as E:
            logging.warning("Snr measure failed: %s" % str(E))
            cell['err'] += 'Snr measure failed: %s\n' % E

        # location
        try:
            location = get_location(summary, cell)
            #location = get_location(summary, ch)  # FIXME
            #location = summary.get_location(ch)
        except Exception as E:
            location = (0, 0, 0)
            logging.warning("Attempt to get location failed: %s" % str(E))
            cell['err'] += 'Attempt to get location failed: %s\n' % E
            #raise E
        cell['ap'] = location[0]
        cell['dv'] = location[1]
        cell['ml'] = location[2]
        cell['location'] = list(location)
        if location != (0, 0, 0):
            try:
                area = get_area(location)
            except Exception as E:
                logging.warning("Failed to get area at (%s): %s" % \
                        (location, E))
                cell['err'] += "Failed to get area at (%s): %s\n" % \
                        (location, E)
                area = 'Fail'
                #raise E
        else:
            area = 'None'
        cell['area'] = area

        if cell['rate'] < min_rate:
            logging.warning("\t%i < min_rate[%i]" % \
                    (cell['rate'], min_rate))
        if cell['nspikes'] < min_spikes:
            logging.warning("\t%i < min_spikes[%i]" % \
                    (cell['nspikes'], min_spikes))
            cell['err'] += "Nspikes < %i" % min_spikes
            logging.error("skipping writing truncated cell")
            #write_cell(cell)
            continue

        # ---------- responsivity ---------------
        baseline, response, stat = get_responsivity(\
                spike_times, ctrials, bwin, rwin)
        cell['baseline_mean'] = numpy.mean(baseline)
        cell['baseline_std'] = numpy.std(baseline)

        cell['driven_mean'] = numpy.mean(response)
        cell['driven_std'] = numpy.std(response)

        cell['ntrials'] = len(ctrials)
        cell['culled_trials'] = n_culled_trials
        cell['responsivity'] = stat

        ctrials = pylab.rec_append_fields(ctrials, \
                ['baseline', 'response'], [baseline, response])

        # find all distractor trials
        dtrials = summary.filter_trials(ctrials, \
                {'name': {'value': 'BlueSquare', 'op': '!='}}, \
                timeRange=trange)
        if len(dtrials) == 0:
            logging.error("Zero trials for %i %i %s" % \
                    (ch, cl, summary._filename))
            cell['err'] += "Zero trials"
            logging.error("skipping writing truncated cell")
            #write_cell(cell)
            continue
        dstims = summary.get_stimuli({'name': \
                {'value': 'BlueSquare', 'op': '!='}})

        # --------- selectivity --------------
        cell['selectivity'] = {}
        cell['separability'] = {}
        for attr in attrs:
            sorted_keys, means, stds, ns, stats = \
                    get_selectivity(summary, dtrials, dstims, attr)
            #max_key = sorted_keys[0]
            cell['selectivity'][attr] = { \
                    'means': means, 'stds': stds, 'ns': ns,
                    'stats': stats, 'sorted': sorted_keys}

        # --------- tolerance ------------
        sorted_keys, means, stds, ns, stats, stimds = \
                get_tolerance(summary, dtrials, dstims)
        cell['tolerance'] = dict(means=means, stds=stds, ns=ns, \
                stats=stats, sorted=sorted_keys)
        cell['stimuli'] = stimds

        try:
            M, ids, trans, stats = get_friedman(summary, dtrials, dstims)
            cell['friedman'] = dict(rmean=M[:, :, 0], rstd=M[:, :, 1], \
                n=M[:, :, 2], bmean=M[:, :, 3], bstd=M[:, :, 4], ids=ids, \
                trans=trans, stats=stats)
        except Exception as E:
            logging.warning("friedman failed: %s" % E)
            cell['err'] += "friedman failed: %s\n" % E
            cell['friedman'] = {}

        try:
            r = M[:, :, 0] - M[:, :, 3]
            cell['separability'] = test_separability(r)
        except Exception as E:
            logging.warning("separability calculation failed: %s" % E)
            cell['err'] += "separability calculation failed: %s\n" % E
            cell['separability'] = {}

        logging.debug("writing full cell")
        write_cell(cell)
        continue


if __name__ == '__main__':
    clear_mongo()
    args = sys.argv[1:]
    if len(args) == 0:
        args = physio.summary.get_summary_filenames()
    sfns = []
    for sfn in args:
        blacklist = False
        for animal in blacklist_animals:
            if animal in sfn:
                blacklist = True
                break
        if not blacklist:
            sfns.append(sfn)

    logging.debug("processing [%i] summary files" % len(sfns))
    logging.debug("%s" % sfns)

    # fetch overrides
    overrides = clustermerge.get_overrides()
    # go through and parse all the potential merges to make sure they're ok
    clustermerge.check_overrides(overrides)

    n_jobs = 1
    Parallel(n_jobs=n_jobs)(delayed(process_summary)(s, overrides) \
            for s in sfns)
