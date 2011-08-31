#!/usr/bin/env python

# import itertools, glob, sys

import numpy as np
# import pylab as pl
import tables

# import pywaveclus

import clock

class Session(object):
    """
    Times are always provided in seconds since beginning of epoch
    """
    def __init__(self, h5filename, samplingrate = 44100):
        self._file = tables.openFile(h5filename,'r')
        self._filename = h5filename
        
        self._samplingrate = samplingrate
        self.read_timebase()
    
    def read_timebase(self):
        matchesNode = self._file.getNode('/TimeMatches')
        # evt_zipper = np.array(matchesNode)
        # audio_offset = matchesNode.attrs.AUDIOOFFSET # is always 0....
        # tb = pixel_clock.TimeBase(evt_zipper, audio_offset)
        # tb.audio_offset = -tb.mw_time_to_audio(epoch_mw[0]) # ? WTF!!!!!!!!!!!!!!
        self._timebase = clock.timebase.TimeBase(np.array(matchesNode))
    
    def close(self):
        self._file.close()
    
    def get_n_cells(self):
        return self._file.root.Cells.nrows
    
    def get_cell(self, i):
        ch, cl = self._file.root.Cells[i]
        return ch, cl
    
    def get_cell_spike_times(self, i, timerange = None):
        ch, cl = self.get_cell(i)
        return self.get_spike_times(ch, cl, timerange)
    
    def get_spike_times(self, channel, cluster, timerange = None):
        n = self._file.getNode('/Channels/ch%i' % channel)
        if timerange is None:
            times = [i['time'] for i in self._file.getNode('/Channels/ch%i' % channel).\
                                        where('clu == %i' % cluster)]
        else:
            assert len(timerange) == 2, "timerange must be length 2: %s" % len(timerange)
            samplerange = (int(timerange[0] * self._samplingrate),
                            int(timerange[1] * self._samplingrate))
            times = [i['time'] for i in self._file.getNode('/Channels/ch%i' % channel).\
                                        where('(clu == %i) & (time > %i) & (time < %i)' \
                                            % (cluster, samplerange[0], samplerange[1]))]
        return np.array(times) / float(self._samplingrate)
    
    def get_events(self, name, timerange = None):
        eventGroup = self._file.getNode('/Events')
        # lookup code (code, name)
        codes = [r['code'] for r in eventGroup.codec.where('name == "%s"' % name)]
        assert len(codes) == 0, "Event name [%s] lookup returned != 1 code [%s]" % (name, len(codes))
        code = codes[0]
        
        # lookup events (code, index, time)
        if timerange is None:
            events = [r.fetch_all_fields() for r in eventGroup.events.where('codes == %i' % code)]
        else:
            assert len(timerange) == 2, "timerange must be length 2: %s" % len(timerange)
            usrange = (int(self._timebase.audio_to_mw(timerange[0]) * 1E6),\
                        int(self._timebase.audio_to_mw(timerange[1]) * 1E6))
            events = [r.fetch_all_fields() for r in eventGroup.events.\
                        where('(codes == %i) & (time > %i) & (time < %i)' \
                            % (code, usrange[0], usrange[1]))]
        indices = [ev[1] for ev in events]
        
        # get values
        values = eventGroup.values[np.array(indices, dtype=int)]
        
        # times
        times = [self._timebase.mw_to_audio(ev[2]) for ev in events]
        return times, values
    
    def get_stimuli(self, matchstr = None, timerange = None):
        pass
    
    def get_blackouts(self):
        pass
    
    def add_blackout(self, beginning, end):
        pass