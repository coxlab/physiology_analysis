import summarize

__all__ = ['summarize']

import logging
import os

import numpy
import tables

from .. import cfg
from .. import session
from .. import spikes


def make_summary_filename(config, session_name, epoch_index):
    return '%s/%s/%s_%i.h5' % (config.get('filesystem', 'resultsrepo'), \
            session_name, session_name, epoch_index)


def get_summary_filenames(config=None):
    if config is None:
        config = cfg.Config()
        config.read_user_config()
    session_names = session.get_sessions(config)
    summary_filenames = []
    for session_name in session_names:
        n_epochs = get_n_epochs(session_name)
        if n_epochs == 0:
            continue
        for epoch_index in xrange(n_epochs):
            summary_filename = make_summary_filename(config, session_name, \
                    epoch_index)
            # check that summary exists
            if os.path.exists(summary_filename):
                summary_filenames.append(summary_filename)
    return summary_filenames


def get_summary_objects(config=None):
    return [Summary(f) for f in get_summary_filenames(config)]


def get_n_epochs(session_name):
    return session.get_n_epochs(session_name)


def load_summary(session_name, epoch_index, config=None):
    if config is None:
        config = cfg.load(session_name)
    summary_filename = make_summary_filename(config, session_name, epoch_index)
    return Summary(summary_filename)


def key_value_to_match(key, value, joiner='|', op='=='):
    vt = type(value)
    if vt in (numpy.ndarray, list, tuple):  # iterables
        return '(%s)' % joiner.join([key_value_to_match(key, i, joiner, op) \
                for i in value])
    elif vt in (float, numpy.float32, numpy.float64, numpy.float128):
        return '(%s %s %f)' % (key, op, value)
    elif vt in (int, numpy.int8, numpy.int16, numpy.int32, numpy.int64):
        return '(%s %s %i)' % (key, op, value)
    elif vt in (str, numpy.string_):
        return '(%s %s "%s")' % (key, op, value)
    else:
        raise TypeError('Unknown type(%s) for value(%s)' % \
                (str(vt), str(value)))


def match_dict_to_match_string(matchDict):
    """
    construct a match string for use with a hdf5 query (readWhere, etc...)
    keys should be various attributes of the table
    values can be of any type
    if value is a dict than it is passed on to key_value_to_match as kwargs
    so
    {'name': {'value': 'BlueSquare', 'op': '!=}} will yield
    key_value_to_match(name, 'BlueSquare', op='!=')
    """
    matches = []
    for k, v in matchDict.iteritems():
        if type(v) is dict:
            vcopy = v.copy()
            value = vcopy.pop('value')
            matches.append(key_value_to_match(k, value, **vcopy))
        else:
            matches.append(key_value_to_match(k, v))
    return '&'.join(matches)


class Summary(object):
    def __init__(self, h5filename):
        self._file = tables.openFile(h5filename, 'r')
        self._filename = h5filename

    def close(self):
        self._file.close()

    def get_epoch_time_range(self, unit):
        pass

    def get_n_channels(self):
        ch_info = self._file.root.SpikeInfo.read(field='ch')
        min_channel = ch_info.min()
        max_channel = ch_info.max()
        return max_channel - min_channel + 1

    def get_channel_indices(self):
        return numpy.unique(self._file.root.SpikeInfo.read( \
                field='ch'))

    def get_n_clusters(self, channel):
        return self._file.root.SpikeInfo.readWhere( \
                'ch == %i' % channel, field='cl').max() + 1

    def get_cluster_indices(self, channel):
        return numpy.unique(self._file.root.SpikeInfo.readWhere( \
                'ch == %i' % channel, field='cl'))

    def get_spike_times(self, channel, cluster, timeRange=None):
        match_string = '(ch == %i) & (cl == %i)' % (channel, cluster)
        if timeRange is not None:
            match_string += ' & (time > %f) & (time < %f)' % \
                    (timeRange[0], timeRange[1])
        return self._file.root.Spikes.readWhere( \
                match_string, field='time')

    def get_waveform(self, channel, cluster):
        w = self._file.root.SpikeInfo.readWhere( \
                '(ch == %i) & (cl == %i)' % (channel, cluster))
        return w['wave_mean'], w['wave_std']

    def get_trials(self, match=None, timeRange=None):
        """
        outcome : 0 = success, 1 = failure
        """
        stimulus_indices = self.get_stimulus_indices(match)
        if len(stimulus_indices) == 0:
            return numpy.array([])
        if timeRange is not None:
            trials = self._file.root.Trials.readWhere( \
                    '(time > %f) & (time < %f)' % \
                    (timeRange[0], timeRange[1]))
        else:
            trials = self._file.root.Trials.read()
        return trials[numpy.in1d(trials['stim_index'], stimulus_indices)]

    def get_stimuli(self, match=None):
        if match is None:
            return self._file.root.Stimuli.read()
        elif type(match) is dict:
            match_string = match_dict_to_match_string(match)
        elif type(match) is str:
            match_string = match
        return self._file.root.Stimuli.readWhere(match_string)

    def get_stimulus_indices(self, match=None):
        if match is None:
            return range(self._file.root.Stimuli.nrows)
        elif type(match) is dict:
            match_string = match_dict_to_match_string(match)
        elif type(match) is str:
            match_string = match
        return self._file.root.Stimuli.getWhereList(match_string)

    def get_channel_locations(self):
        return self._file.root.Locations.read()

    def get_gaze(self, timeRange=None):
        if timeRange is None:
            return self._file.root.Gaze.read()
        return self._file.root.Gaze.readWhere(\
                '(time > %f) & (time < %f)' %\
                (timeRange[0], timeRange[1]))

    def get_epoch_range(self):
        return self._file.root._v_attrs['au_start'], \
                self._file.root._v_attrs['au_end']

    def get_source_md5sum(self):
        return self._file.root._v_attrs['src_md5']

    def get_md5sum(self):
        return os.popen('md5sum %s' % self._filename).read().split()[0]

    def get_significant_bins(self, ch, cl, binw=0.05, bin_alpha=0.001, \
            trials=None, attr="name", blacklist="BlueSquare", \
            spike_times=None):
        if spike_times is None:
            spike_times = self.get_spike_times(ch, cl)
        if trials is None:
            if len(blacklist):
                match_dict = {attr: {'value': blacklist, 'op': '!=', \
                        'joiner': '&'}}
            else:
                match_dict = {}
            trials = self.get_trials(match_dict)
            if len(trials) == 0:
                logging.warning("No trials found")
                return []
        duration = trials[0]['duration'] / 1000.
        return spikes.triallock.find_significant_bins(spike_times, \
                trials['time'], duration, binw, bin_alpha)

    def get_binned_response(self, ch, cl, attr, bins=None, binw=0.05, \
            blacklist="BlueSquare", spike_times=None):
        # get unique stimuli
        if len(blacklist):
            match_dict = {attr: {'value': blacklist, 'op': '!=', \
                    'joiner': '&'}}
        else:
            match_dict = {}
        uniques = numpy.unique(self.get_stimuli(match_dict)[attr])
        if len(uniques) == 0:
            logging.warning("No stimuli found")
            return {}, {}, {}, {}
        if spike_times is None:
            spike_times = self.get_spike_times(ch, cl)
        if bins is None:
            self.get_significant_bins(ch, cl, binw, attr=attr, \
                    blacklist=blacklist, spike_times=spike_times)
        if len(bins) == 0:
            logging.warning("Tried to bin with 0 bins")
            return {}, {}, {}, {}
        means = {}
        stds = {}
        ns = {}
        responses = {}
        for unique in uniques:
            trials = self.get_trials({attr: unique})
            if len(trials) == 0:
                means[unique] = numpy.nan
                stds[unique] = numpy.nan
                ns[unique] = 0
                responses[unique] = numpy.nan
                continue
            duration = trials[0]['duration'] / 1000.
            m, s = spikes.triallock.bin_response(spike_times, trials['time'], \
                    binw, duration, binw)
            means[unique] = m
            stds[unique] = s
            ns[unique] = len(trials)
            responses[unique] = (numpy.sum(m[bins]) / float(len(bins)) - \
                    m[0]) / ns[unique]
        return responses, means, stds, ns

    def get_response_matrix(self, ch, cl, attr1, attr2, bins=None, \
            binw=0.05, spike_times=None, stims=None, uniques1=None, \
            uniques2=None):
        if stims is None:
            stims = self.get_stimuli()
        if spike_times is None:
            spike_times = self.get_spike_times(ch, cl)
        if bins is None:
            bins = self.get_significant_bins(ch, cl, binw, \
                    spike_times=spike_times)
        if uniques1 is None:
            uniques1 = numpy.unique(stims[attr1])
            uniques1.sort()
        if uniques2 is None:
            uniques2 = numpy.unique(stims[attr2])
            uniques2.sort()
        M = numpy.empty((len(uniques1), len(uniques2)))
        for (i1, u1) in enumerate(uniques1):
            for (i2, u2) in enumerate(uniques2):
                trials = self.get_trials({attr1: u1, \
                        attr2: u2})
                if len(trials) == 0:
                    logging.warning("No trials for %s by %s" % \
                            (u1, u2))
                    M[i1, i2] = numpy.nan
                    continue
                duration = trials[0]['duration'] / 1000.
                m, s = spikes.triallock.bin_response(spike_times, \
                        trials['time'], binw, duration, binw)
                M[i1, i2] = numpy.sum(m[bins]) / float(len(bins)) - m[0]
        return M
