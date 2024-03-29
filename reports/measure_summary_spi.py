#!/usr/bin/env python

import logging
import os
import pickle

logging.basicConfig(level=logging.DEBUG)

import pylab
import numpy

from joblib import Parallel, delayed

import physio

#summaries = physio.summary.get_summary_objects()
summary_filenames = [sf for sf in physio.summary.get_summary_filenames() \
        if not (('fake' in sf) or ('H3' in sf) or ('H4' in sf) or \
        ('H7' in sf) or ('H8' in sf))]

min_spikes = 10
min_rate = 0.01  # hz
#rwin = (0.05, 0.2)
# default_bins = None
default_bins = [2, 3, 4]  # corresponds to 0.05 to 0.20 with binw 0.05
# bin[0] is baseline
prew = 0.1  # for baseline calculation

attrs = ['name', 'pos_x', 'pos_y', 'size_x', 'rotation']

resultsdir = 'summary_results'

mongo_server = 'soma2.rowland.org'
mongo_db = 'physiology'
mongo_collection = 'cells'


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


def get_responsivity():
    pass


def get_selectivity(resps, means, ns):
    pass


def get_tolerance():
    pass


# have this dump directly to mongo (remove plotting)
def process_summary(summary_filename):
    if ('fake' in summary_filename) or \
            ('H3' in summary_filename) or \
            ('H4' in summary_filename) or \
            ('H7' in summary_filename) or \
            ('H8' in summary_filename):
        logging.debug("Skipping %s" % summary_filename)
        return
    summary = physio.summary.Summary(summary_filename)
    logging.debug("Processing %s" % summary._filename)

    # cull trials by success
    trials = summary.get_trials()
    if len(trials) == 0:
        logging.error("No trails for %s" % summary._filename)
        return
    trials = trials[trials['outcome'] == 0]
    # and gaze
    gaze = clean_gaze(summary.get_gaze())

    if len(gaze) > 0:
        logging.debug("N Trials before gaze culling: %i" % len(trials))
        trials = cull_trials_by_gaze(trials, gaze)
        logging.debug("N Trials after gaze culling: %i" % len(trials))

    for ch in xrange(1, 33):
        for cl in summary.get_cluster_indices(ch):
            outdir = '%s/%s_%i_%i' % \
                    (resultsdir, os.path.basename(summary._filename), ch, cl)

            info_dict = {}

            logging.debug("ch: %i, cl: %i" % (ch, cl))
            # rate
            spike_times = summary.get_spike_times(ch, cl)

            # find start of isolation
            isolation_start = physio.spikes.times.\
                    find_isolation_start_by_isi(spike_times)
            spike_times = spike_times[spike_times >= isolation_start]

            nspikes = len(spike_times)
            info_dict['nspikes'] = nspikes
            if nspikes < min_spikes:
                logging.warning("\t%i < min_spikes[%i]" % \
                        (nspikes, min_spikes))
                continue
            trange = (spike_times.min(), spike_times.max())
            # trange = summary.get_epoch_range()
            rate = nspikes / (trange[1] - trange[0])
            info_dict['rate'] = rate
            if rate < min_rate:
                logging.warning("\t%i < min_rate[%i]" % \
                        (rate, min_rate))
                continue

            # filter trials
            dtrials = summary.filter_trials(trials, \
                    {'name': {'value': 'BlueSquare', 'op': '!='}}, \
                    timeRange=trange)
            if len(dtrials) == 0:
                logging.error("Zero trials for %i %i %s" % \
                        (ch, cl, summary._filename))
                continue

            # snr TODO

            # location
            try:
                location = summary.get_location(ch)
            except Exception as E:
                location = (0, 0, 0)
                print "Attempt to get location failed: %s" % str(E)
            info_dict['location'] = list(location)

            # significant bins
            #bins = summary.get_significant_bins(ch, cl, attr="name", \
            #        blacklist="BlueSquare", spike_times=spike_times, \
            #        timeRange=trange)
            if default_bins is None:
                bins = summary.get_significant_bins(ch, cl, trials=dtrials, \
                        spike_times=spike_times)
            else:
                bins = default_bins
            info_dict['bins'] = bins

            baseline = summary.get_baseline(ch, cl, prew, trials=trials, \
                    spike_times=spike_times)
            info_dict['baseline'] = baseline

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

            if not os.path.exists(outdir):
                os.makedirs(outdir)
            with open(outdir + '/info_dict.p', 'w') as f:
                pickle.dump(info_dict, f, 2)

            with open(outdir + '/sel_info.p', 'w') as f:
                pickle.dump({'resps': resps, 'means': means, 'stds': stds, \
                        'ns': ns}, f, 2)

            x = pylab.arange(len(resps))
            y = pylab.zeros(len(resps))
            err = pylab.zeros(len(resps))
            pylab.figure(1)
            for (i, name) in enumerate(sorted_names):
                y[i] = resps[name]
                # TODO fix this to be something reasonable
                #err[i] = (pylab.sum(stds[name][bins]) / float(len(bins))) / \
                #        pylab.sqrt(ns[name])
                err[i] = 0
            pylab.errorbar(x, y, err)
            xl = pylab.xlim()
            pylab.xticks(x, sorted_names)
            pylab.xlim(xl)
            pylab.ylabel('average binned response')
            pylab.title('Selectivity: %.2f' % sel_index)
            pylab.savefig(outdir + '/by_name.png')
            pylab.close(1)

            # separability
            # get stims without bluesquare
            stims = summary.get_stimuli({'name': \
                    {'value': 'BlueSquare', 'op': '!='}})
            attr_combinations = {}
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


#Parallel(n_jobs=1)(delayed(process_summary)(s) for s in summary_filenames)
Parallel(n_jobs=-1)(delayed(process_summary)(s) for s in summary_filenames)
