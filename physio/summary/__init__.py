import summarize

__all__ = ['summarize']


import numpy

import tables

def load_summary(session_name, epoch):
    pass

def key_value_to_match(key, value, joiner='|'):
    vt = type(value)
    if vt in (numpy.ndarray, list, tuple): # iterables
        return '(%s)' % joiner.join([key_value_to_match(key, i, '|') \
                for i in value])
    elif vt in (float, numpy.float32, numpy.float64, numpy.float128):
        return '(%s == %f)' % (key, value)
    elif vt in (int, numpy.int8, numpy.int16, numpy.int32, numpy.int64):
        return '(%s == %i)' % (key, value)
    elif vt == str:
        return '(%s == "%s")' % (key, value)
    else:
        raise TypeError('Unknown type(%s) for value(%s)' % \
                (str(vt), str(value)))

def match_dict_to_match_string(matchDict):
    return '&'.join([key_value_to_match(k,v) \
            for k, v in matchDict.iteritems()])

class Summary(object):
    def __init__(self, h5filename):
        self._file = tables.openFile(h5filename, 'r')
        self._filename = h5filename

    def close(self):
        self._file.close()

    def get_epoch_time_range(self, unit):
        pass
    
    def get_n_channels(self):
        return self._file.root.Spikes.read(field = 'ch').max() + 1

    def get_channel_indices(self):
        return numpy.unique(self._file.root.Spikes.read(\
                field = 'ch'))

    def get_n_clusters(self, channel):
        return self._file.root.Spikes.readWhere(\
                'ch == %i' % channel, field = 'cl').max() + 1

    def get_cluster_indices(self, channel):
        return numpy.unique(self._file.root.Spikes.readWhere( \
                'ch == %i' % channel, field = 'cl'))

    def get_spike_times(self, channel, cluster, timeRange = None):
        match_string = '(ch == %i) & (cl == %i)' % (channel, cluster)
        if timeRange is not None:
            match_string += ' & (time > %f) & (time < %f)' % \
                    (timeRange[0], timeRange[1])
        return self._file.root.Spikes.readWhere( \
                match_string, field = 'time')

    def get_trials(self, matchDict = None, timeRange = None):
        stimulus_indices = self.get_stimulus_indices(matchDict)
        if len(stimulus_indices) == 0:
            return numpy.array([])
        if timeRange is not None:
            trials = self._file.root.Trials.readWhere( \
                    '(time > %f) & (time < %f)' % \
                    (timeRange[0], timeRange[1]))
        else:
            trials = self._file.root.Trials.read()
        return trials[numpy.in1d(trials['stim_index'], stimulus_indices)]

    def get_stimuli(self, matchDict = None):
        if matchDict is None:
            return self._file.root.Stimuli.read()
        match_string = match_dict_to_match_string(matchDict)
        return self._file.root.Stimuli.readWhere(match_string)

    def get_stimulus_indices(self, matchDict = None):
        if matchDict is None:
            return range(self._file.root.Stimuli.nrows)
        match_string = match_dict_to_match_string(matchDict)
        return self._file.root.Stimuli.getWhereList(match_string)

    def get_channel_locations(self):
        return self._file.root.Locations.read()

    def get_gaze(self, timeRange = None):
        if timeRange is None:
            return self._file.root.Gaze.read()
        return self._file.root.Gaze.readWhere(\
                '(time > %f) & (time < %f)' %\
                (timeRange[0], timeRange[1]))