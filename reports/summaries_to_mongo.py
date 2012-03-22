#!/usr/bin/env python

import logging
import os
import pickle

logging.basicConfig(level=logging.DEBUG)

import pylab
import numpy
import pymongo
import scipy.stats

from joblib import Parallel, delayed

import physio


blacklist_animals = ['fake', 'H3', 'H4', 'H7', 'H8']

min_spikes = 100
min_rate = 0.01  # hz
rwin = (0.05, 0.2)
bwin = (-0.15, 0.0)

attrs = ['name', 'pos_x', 'pos_y', 'size_x', 'rotation']

mongo_server = 'soma2.rowland.org'
mongo_db = 'physiology'
mongo_collection = 'cells_sel'


def make_mongo_safe(d):
    t = type(d)
    if t == dict:
        nd = {}
        for k in d.keys():
            nk = str(k)
            nk = nk.replace('.', ',')
            nd[nk] = make_mongo_safe(d[k])
            #d[k] = make_mongo_safe(d[k])
        return nd
        #return d
    elif t == list:
        return [make_mongo_safe(i) for i in d]
    elif t == tuple:
        return tuple(make_mongo_safe(list(d)))
    elif t == numpy.ndarray:
        return make_mongo_safe(list(d))
    elif t in (bool, numpy.bool_):
        return bool(d)
    elif numpy.issubdtype(t, int):
        return int(d)
    elif t in [numpy.uint, numpy.uint8, numpy.uint16, numpy.uint32,\
            numpy.uint64]:
        return int(d)
    elif numpy.issubdtype(t, float):
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
    return conditions, stat


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


def get_tolerance():
    pass


# have this dump directly to mongo (remove plotting)
def process_summary(summary_filename):
    summary = physio.summary.Summary(summary_filename)
    logging.debug("Processing %s" % summary._filename)

    fn = os.path.basename(summary_filename)
    animal = fn.split('_')[0]
    date = fn.split('_')[1]
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
        for cl in summary.get_cluster_indices(ch):
            ctrials = trials.copy()
            cell = {}
            cell['ch'] = ch
            cell['cl'] = cl
            cell['animal'] = animal
            cell['date'] = date

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
            for attr in attrs:
                conditions, stats = get_selectivity(summary, \
                        dtrials, dstims, attr)
                cell['selectivity'][attr] = {'conditions': conditions, \
                        'stats': stats}

            # --------- tolerance ------------

            write_cell(cell)
            continue

            # selectivity
            #resps, means, stds, ns = summary.get_binned_response( \
            #        ch, cl, 'name', bins=bins, spike_times=spike_times, \
            #        blacklist="BlueSquare", timeRange=trange)
            resps, means, stds, ns = summary.get_binned_response( \
                    ch, cl, 'name', bins=bins, spike_times=spike_times, \
                    trials=dtrials, timeRange=trange)
            if len(resps) == 0:
                logging.warning("No responses")
                continue
            sel_index = physio.spikes.selectivity.selectivity(resps.values())
            #if numpy.isnan(sel_index):
            #    raise Exception("Selectivity is nan")
            sorted_names = sorted(resps, key=lambda k: resps[k])
            info_dict['selectivity'] = sel_index
            info_dict['sorted_names'] = sorted_names

            # separability
            # get stims without bluesquare
            stims = summary.get_stimuli({'name': \
                    {'value': 'BlueSquare', 'op': '!='}})
            sep_info = {}
            for (ai, attr1) in enumerate(attrs[:-1]):
                uniques1 = numpy.unique(stims[attr1])
                for attr2 in attrs[ai + 1:]:
                    uniques2 = numpy.unique(stims[attr2])
                    if attr1 == attr2:
                        continue
                    M = summary.get_response_matrix(ch, cl, attr1, attr2, \
                            bins=bins, spike_times=spike_times, stims=stims, \
                            uniques1=uniques1, uniques2=uniques2, \
                            timeRange=trange, trials=dtrials)
                    if M.shape[0] == 1 or M.shape[1] == 1:
                        logging.warning("M.shape %s, skipping" % \
                                str(M.shape))
                        continue
                    sep, spi, ps = physio.spikes.separability.\
                            separability_permutation(M)
                    if not pylab.any(pylab.isnan(M)):
                        pylab.figure(1)
                        pylab.imshow(M, interpolation='nearest')
                        pylab.colorbar()
                        pylab.xlabel(attr2)
                        xl = pylab.xlim()
                        yl = pylab.ylim()
                        pylab.xticks(range(len(uniques2)), uniques2)
                        pylab.ylabel(attr1)
                        pylab.yticks(range(len(uniques1)), uniques1)
                        pylab.xlim(xl)
                        pylab.ylim(yl)
                        pylab.title('Sep: %s, %.4f, (%.3f, %.3f)' % \
                                (str(sep), spi, ps[0], ps[1]))
                        pylab.savefig(outdir + '/%s_%s.png' % \
                                (attr1, attr2))
                        pylab.close(1)
                    sep_info['_'.join((attr1, attr2))] = { \
                            'sep': sep, 'spi': spi, 'ps': ps}

            with open(outdir + '/sep_info.p', 'w') as f:
                pickle.dump(sep_info, f, 2)

            # compute separability at each name
            name_sep_info = {}
            for name in sorted_names:
                stims = summary.get_stimuli({'name': name})
                for (ai, attr1) in enumerate(attrs[:-1]):
                    uniques1 = numpy.unique(stims[attr1])
                    for attr2 in attrs[ai + 1:]:
                        uniques2 = numpy.unique(stims[attr2])
                        if attr1 == attr2 or \
                                attr1 == 'name' or attr2 == 'name':
                            continue
                        M = summary.get_response_matrix(ch, cl, attr1, \
                                attr2, bins=bins, spike_times=spike_times,\
                                stims=stims, uniques1=uniques1, \
                                uniques2=uniques2, timeRange=trange, \
                                trials=dtrials)
                        if M.shape[0] == 1 or M.shape[1] == 1:
                            logging.debug("M.shape incompatible" \
                                    " with separability: %s" % \
                                    str(M.shape))
                            continue
                        else:
                            sep, spi, ps = physio.spikes.separability.\
                                    separability_permutation(M)
                            if not pylab.any(pylab.isnan(M)):
                                pylab.figure(1)
                                pylab.imshow(M, interpolation='nearest')
                                pylab.colorbar()
                                pylab.xlabel(attr2)
                                xl = pylab.xlim()
                                yl = pylab.ylim()
                                pylab.xticks(range(len(uniques2)), uniques2)
                                pylab.ylabel(attr1)
                                pylab.yticks(range(len(uniques1)), uniques1)
                                pylab.xlim(xl)
                                pylab.ylim(yl)
                                pylab.title('Sep: %s, %.4f, (%.3f, %.3f)' \
                                        % (str(sep), spi, ps[0], ps[1]))
                                pylab.savefig(outdir + '/%s_%s_%s.png' % \
                                        (name, attr1, attr2))
                                pylab.close(1)
                            name_sep_info['_'.join((name, attr1, attr2))] \
                                    = {'sep': sep, 'spi': spi, 'ps': ps}

            with open(outdir + '/name_sep_info.p', 'w') as f:
                pickle.dump(name_sep_info, f, 2)


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
