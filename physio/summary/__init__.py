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
        tokens = os.path.basename(self._filename).split('_')
        self.animal = tokens[0]
        if len(tokens) > 1:
            self.date = tokens[1]
        else:
            self.date = ''
        if len(tokens) > 2:
            self.epoch = tokens[2]
        else:
            self.epoch = ''
        self.session = '%s_%s' % (self.animal, self.date)

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

    def get_spikes(self, channel, cluster=None, timeRange=None):
        m = '(ch == %i)' % channel
        if cluster is not None:
            m += ' & (cl == %i)' % cluster
        if timeRange is not None:
            m += ' & (time > %f) & (time < %f)' % \
                    (timeRange[0], timeRange[1])
        return self._file.root.Spikes.readWhere(m)

    def get_spike_times(self, channel, cluster, timeRange=None):
        match_string = '(ch == %i) & (cl == %i)' % (channel, cluster)
        if timeRange is not None:
            match_string += ' & (time > %f) & (time < %f)' % \
                    (timeRange[0], timeRange[1])
        return self._file.root.Spikes.readWhere( \
                match_string, field='time')

    def get_spike_snrs(self, channel, cluster, timeRange=None):
        match_string = '(ch == %i) & (cl == %i)' % (channel, cluster)
        if timeRange is not None:
            match_string += ' & (time > %f) & (time < %f)' % \
                    (timeRange[0], timeRange[1])
        return self._file.root.Spikes.readWhere( \
                match_string, field='snr')

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

    def get_location(self, ch):
        """
        Channel index in tdt indices
        so tip is channel 7, then 10, then 1... then 29

        Returns
        -------
            ap, dv, ml
        """
        # saved indices are in audio not tdt so take tdt -1 to get audio
        if ch < 1 or ch > 32:
            raise ValueError("Incorrect index [not in 1 to 32]: %i" % ch)
        return self._file.root.Locations.read()[ch - 1]

    def get_gaze(self, timeRange=None):
        if timeRange is None:
            return self._file.root.Gaze.read()
        return self._file.root.Gaze.readWhere(\
                '(time > %f) & (time < %f)' %\
                (timeRange[0], timeRange[1]))

    def get_events(self, timeRange=None):
        if timeRange is None:
            return self._file.root.Events.read()
        return self._file.root.Events.readWhere(\
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
            spike_times=None, timeRange=None):
        if spike_times is None:
            spike_times = self.get_spike_times(ch, cl, timeRange)
        if trials is None:
            if len(blacklist):
                match_dict = {attr: {'value': blacklist, 'op': '!=', \
                        'joiner': '&'}}
            else:
                match_dict = {}
            trials = self.get_trials(match_dict, timeRange=timeRange)
            if len(trials) == 0:
                logging.warning("No trials found")
                return []
        duration = trials[0]['duration'] / 1000.
        return spikes.triallock.find_significant_bins(spike_times, \
                trials['time'], duration, binw, bin_alpha)

    def get_binned_response(self, ch, cl, attr, bins=None, binw=0.05, \
            blacklist="BlueSquare", spike_times=None, timeRange=None, \
            trials=None):
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
            spike_times = self.get_spike_times(ch, cl, timeRange)
        if bins is None:
            bins = self.get_significant_bins(ch, cl, binw, attr=attr, \
                    blacklist=blacklist, spike_times=spike_times, \
                    timeRange=timeRange)
        if len(bins) == 0:
            logging.warning("Tried to bin with 0 bins")
            return {}, {}, {}, {}
        if trials is None:
            trials = self.get_trials(match_dict, timeRange=timeRange)
        means = {}
        stds = {}
        ns = {}
        responses = {}
        for unique in uniques:
            utrials = self.filter_trials(trials, {attr: unique})
            #trials = self.get_trials({attr: unique}, timeRange=timeRange)
            if len(utrials) == 0:
                means[unique] = numpy.nan
                stds[unique] = numpy.nan
                ns[unique] = 0
                responses[unique] = numpy.nan
                continue
            duration = utrials[0]['duration'] / 1000.
            m, s = spikes.triallock.bin_response(spike_times, utrials['time'],\
                    binw, duration, binw)
            means[unique] = m
            stds[unique] = s
            ns[unique] = len(utrials)
            responses[unique] = (numpy.sum(m[bins]) / float(len(bins)) - \
                    m[0])
        return responses, means, stds, ns

    def get_response_matrix(self, ch, cl, attr1, attr2, bins=None, \
            binw=0.05, spike_times=None, stims=None, uniques1=None, \
            uniques2=None, timeRange=None, trials=None):
        if stims is None:
            stims = self.get_stimuli()
        if spike_times is None:
            spike_times = self.get_spike_times(ch, cl, timeRange)
        if bins is None:
            bins = self.get_significant_bins(ch, cl, binw, \
                    spike_times=spike_times, timeRange=timeRange)
        if uniques1 is None:
            uniques1 = numpy.unique(stims[attr1])
            uniques1.sort()
        if uniques2 is None:
            uniques2 = numpy.unique(stims[attr2])
            uniques2.sort()
        if trials is None:
            trials.get_trials({}, timeRange=timeRange)
        M = numpy.empty((len(uniques1), len(uniques2)))
        for (i1, u1) in enumerate(uniques1):
            for (i2, u2) in enumerate(uniques2):
                utrials = self.filter_trials(trials, {attr1: u1, \
                        attr2: u2})
                #trials = self.get_trials({attr1: u1, \
                #        attr2: u2}, timeRange=timeRange)
                if len(utrials) == 0:
                    logging.warning("No trials for %s by %s" % \
                            (u1, u2))
                    M[i1, i2] = numpy.nan
                    continue
                duration = utrials[0]['duration'] / 1000.
                m, s = spikes.triallock.bin_response(spike_times, \
                        utrials['time'], binw, duration, binw)
                M[i1, i2] = numpy.sum(m[bins]) / float(len(bins)) - m[0]
        return M

    def get_baseline(self, ch, cl, prew, trials=None, spike_times=None, \
            timeRange=None, raw=False):
        if trials is None:
            trials = self.get_trials({}, timeRange=timeRange)
        if spike_times is None:
            spike_times = self.get_spike_times(ch, cl, timeRange)
        per_trial = numpy.zeros(len(trials))
        for (i, tt) in enumerate(trials['time']):
            n = numpy.sum(numpy.logical_and(spike_times > (tt - prew), \
                    spike_times < tt))
            per_trial[i] = n
        if raw:
            return per_trial
        total = numpy.sum(per_trial)
        if total == 0:
            return 0
        return total / (len(trials) * prew)

    def filter_trials_by_stim_index(self, trials, index, timeRange=None):
        ftrials = trials[numpy.in1d(trials['stim_index'], index)]
        if timeRange is not None:
            ftrials = ftrials[numpy.logical_and( \
                    ftrials['time'] > timeRange[0], \
                    ftrials['time'] < timeRange[1])]
        return ftrials

    def filter_trials(self, trials, match=None, timeRange=None):
        sis = self.get_stimulus_indices(match)
        if len(sis) == 0:
            return numpy.array([])
        return self.filter_trials_by_stim_index(trials, sis, timeRange)

    def filter_trials_by_stim(self, trials, stim, timeRange=None):
        if hasattr(stim, 'dtype'):  # stim
            keys = dict(stim.dtype.fields).keys()
            match = dict([(k, stim[k]) for k in keys])
            return self.filter_trials(trials, match, timeRange)
        else:
            raise TypeError("stim[%s] does not have a dtype attribute" % stim)

    def fill_trials(self, trials):
        """ fill in stimulus characteristics for an array of trials """
        raise NotImplementedError
