#!/usr/bin/env python

import datetime
import logging
import os

logging.basicConfig(level=logging.DEBUG)

import pylab
import numpy
import pymongo
import scipy.stats

from joblib import Parallel, delayed

import physio

import brainatlas


blacklist_animals = ['fake', 'H3', 'H4', 'H7', 'H8']

min_spikes = 100
min_rate = 0.01  # hz
rwin = (0.05, 0.2)
bwin = (-0.15, 0.0)

attrs = ['name', 'pos_x', 'pos_y', 'size_x', 'rotation']

mongo_server = 'coxlabanalysis1.rowland.org'
mongo_db = 'physiology'
mongo_collection = 'cells_sep'


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
        print "kruskal failed with: %s" % str(e)

    try:
        #F, p2 = scipy.stats.f_oneway(*all_sqrt_counts)
        F, p2 = scipy.stats.f_oneway(*responses)
        print ("anova F=%f, p=%f" % (F, p2))
    except Exception as e:
        print "anova failed with: %s" % str(e)

    try:
        lens = [len(r) for r in responses]
        trunced = [numpy.array(r[0:numpy.min(lens)]) for r in responses]
        X, p3 = scipy.stats.friedmanchisquare(*trunced)
        print ("friedman=%f, p=%f" % (X, p3))
    except Exception as e:
        print "friedman failed with: %s" % str(e)

    try:
        mr = [numpy.mean(r) for r in responses]
        sel_index = physio.spikes.selectivity.selectivity(mr)
    except Exception as e:
        print "selectivity failed with: %s" % str(e)

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


def get_area(location):
    ap, dv, ml = location
    areas = 'V2L AuD Au1 AuV PRh V1B V1M TeA Ect'.split()
    cs = brainatlas.section.get_closest_section(ap, areas=areas)
    area = cs.get_area_for_location(ml, dv, 'skull')
    return area


# have this dump directly to mongo (remove plotting)
def process_summary(summary_filename):
    summary = physio.summary.Summary(summary_filename)
    logging.debug("Processing %s" % summary._filename)

    fn = os.path.basename(summary_filename)
    animal = fn.split('_')[0]
    date = fn.split('_')[1]
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
        print "Fetching gaze failed: %s" % E
        gaze = []

    if len(gaze) > 0:
        logging.debug("N Trials before gaze culling: %i" % len(trials))
        trials = cull_trials_by_gaze(trials, gaze)
        logging.debug("N Trials after gaze culling: %i" % len(trials))

    for ch in xrange(1, 33):
        try:
            cis = summary.get_cluster_indices(ch)
        except Exception as E:
            print "Getting cluster_indices failed: %s" % E
            continue
        for cl in cis:
            ctrials = trials.copy()
            cell = {}
            cell['ch'] = ch
            cell['cl'] = cl
            cell['animal'] = animal
            cell['date'] = date
            cell['datetime'] = dt

            logging.debug("ch: %i, cl: %i" % (ch, cl))
            # rate
            spike_times = summary.get_spike_times(ch, cl)

            # find start of isolation
            isolation_start = physio.spikes.times.\
                    find_isolation_start_by_isi(spike_times)
            spike_times = spike_times[spike_times >= isolation_start]

            nspikes = len(spike_times)
            cell['nspikes'] = nspikes
            if nspikes < min_spikes:
                logging.warning("\t%i < min_spikes[%i]" % \
                        (nspikes, min_spikes))
                #write_cell(cell)
                continue

            trange = (spike_times.min(), spike_times.max())
            # trange = summary.get_epoch_range()
            rate = nspikes / (trange[1] - trange[0])
            cell['rate'] = rate
            if rate < min_rate:
                logging.warning("\t%i < min_rate[%i]" % \
                        (rate, min_rate))
                write_cell(cell)
                continue
            cell['trange'] = trange

            # snr TODO
            try:
                snrs = summary.get_spike_snrs(ch, cl, timeRange=trange)
                cell['snr_mean'] = numpy.mean(snrs)
                cell['snr_std'] = numpy.std(snrs)
            except Exception as E:
                print "Snr measure failed: %s" % str(E)

            # location
            try:
                location = summary.get_location(ch)
            except Exception as E:
                location = (0, 0, 0)
                print "Attempt to get location failed: %s" % str(E)
            cell['location'] = list(location)
            if location != (0, 0, 0):
                try:
                    area = get_area(location)
                except Exception as E:
                    print "Failed to get area: %s" % E
                    area = 'Na'
            else:
                area = 'Na'
            cell['area'] = area

            # ---------- responsivity ---------------
            baseline, response, stat = get_responsivity(\
                    spike_times, ctrials, bwin, rwin)
            cell['baseline_mean'] = numpy.mean(baseline)
            cell['baseline_std'] = numpy.std(baseline)

            cell['driven_mean'] = numpy.mean(response)
            cell['driven_std'] = numpy.std(response)

            cell['ntrials'] = len(ctrials)
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
                continue
            dstims = summary.get_stimuli({'name': \
                    {'value': 'BlueSquare', 'op': '!='}})

            # --------- selectivity --------------
            cell['selectivity'] = {}
            cell['separability'] = {}
            for attr in attrs:
                sorted_keys, means, stds, ns, stats = \
                        get_selectivity(summary, dtrials, dstims, attr)
                max_key = sorted_keys[0]
                cell['selectivity'][attr] = { \
                        'means': means, 'stds': stds, 'ns': ns,
                        'stats': stats, 'sorted': sorted_keys}
                cell['separability'][attr] = {}

                atrials = summary.filter_trials(dtrials, {attr: max_key})
                for attr2 in attrs:
                    if attr == attr2:
                        continue

                    # this is only for the MAX
                    sorted_keys, means, stds, ns, stats = \
                            get_selectivity(summary, atrials, dstims, attr2)
                    max_key = sorted_keys[0]
                    cell['selectivity'][attr][attr2] = { \
                            'means': means, 'stds': stds, 'ns': ns,
                            'stats': stats, 'sorted': sorted_keys}

                    # ----------- separability --------------
                    # this is for all
                    M, S, N, L, stats = get_separability(summary, dtrials, \
                            dstims, attr, attr2)
                    cell['separability'][attr][attr2] = \
                            {'M': M, 'S': S, 'N': N, 'stats': stats}

            # --------- tolerance ------------
            sorted_keys, means, stds, ns, stats, stimds = \
                    get_tolerance(summary, dtrials, dstims)
            cell['tolerance'] = dict(means=means, stds=stds, ns=ns, \
                    stats=stats, sorted=sorted_keys)
            cell['stimuli'] = stimds

            write_cell(cell)
            continue


if __name__ == '__main__':
    clear_mongo()
    sfns = []
    for sfn in physio.summary.get_summary_filenames():
        blacklist = False
        for animal in blacklist_animals:
            if animal in sfn:
                blacklist = True
                break
        if not blacklist:
            sfns.append(sfn)

    print "processing [%i] summary files" % len(sfns)
    print sfns

    #Parallel(n_jobs=1)(delayed(process_summary)(s) for s in sfns)
    Parallel(n_jobs=-1)(delayed(process_summary)(s) for s in sfns)
