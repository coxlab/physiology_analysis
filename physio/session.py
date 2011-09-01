#!/usr/bin/env python

# import itertools, glob, sys

import numpy as np
# import pylab as pl
import tables

# import pywaveclus

import clock
import h5

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
        # evt_zipper = np.array(matchesNode)
        # audio_offset = matchesNode.attrs.AUDIOOFFSET # is always 0....
        # tb = pixel_clock.TimeBase(evt_zipper, audio_offset)
        # tb.audio_offset = -tb.mw_time_to_audio(epoch_mw[0]) # ? WTF!!!!!!!!!!!!!!
        matchesNode = self._file.getNode('/TimeMatches')
        # matches = np.array(matchesNode)
        self._timebase = clock.timebase.TimeBase(np.array(matchesNode))
    
    def close(self):
        self._file.close()
    
    def get_n_cells(self):
        return self._file.root.Cells.nrows
    
    def get_cell(self, i):
        ch, cl = self._file.root.Cells[i]
        return ch, cl
    
    def get_cell_spike_times(self, i, timeRange = None):
        ch, cl = self.get_cell(i)
        return self.get_spike_times(ch, cl, timeRange)
    
    def get_spike_times(self, channel, cluster, timeRange = None):
        n = self._file.getNode('/Channels/ch%i' % channel)
        if timeRange is None:
            times = [i['time'] for i in self._file.getNode('/Channels/ch%i' % channel).\
                                        where('clu == %i' % cluster)]
        else:
            assert len(timeRange) == 2, "timeRange must be length 2: %s" % len(timeRange)
            samplerange = (int(timeRange[0] * self._samplingrate),
                            int(timeRange[1] * self._samplingrate))
            times = [i['time'] for i in self._file.getNode('/Channels/ch%i' % channel).\
                                        where('(clu == %i) & (time > %i) & (time < %i)' \
                                            % (cluster, samplerange[0], samplerange[1]))]
        return np.array(times) / float(self._samplingrate)
    
    def get_events(self, name, timeRange = None):
        return h5.events.read_events(self._file, name, timeRange)
        # eventGroup = self._file.getNode('/Events')
        # # lookup code (code, name)
        # codes = [r['code'] for r in eventGroup.codec.where('name == "%s"' % name)]
        # assert len(codes) == 0, "Event name [%s] lookup returned != 1 code [%s]" % (name, len(codes))
        # code = codes[0]
        # 
        # # lookup events (code, index, time)
        # if timeRange is None:
        #     events = [r.fetch_all_fields() for r in eventGroup.events.where('codes == %i' % code)]
        # else:
        #     assert len(timeRange) == 2, "timeRange must be length 2: %s" % len(timeRange)
        #     usrange = (int(self._timebase.audio_to_mw(timeRange[0]) * 1E6),\
        #                 int(self._timebase.audio_to_mw(timeRange[1]) * 1E6))
        #     events = [r.fetch_all_fields() for r in eventGroup.events.\
        #                 where('(codes == %i) & (time > %i) & (time < %i)' \
        #                     % (code, usrange[0], usrange[1]))]
        # indices = [ev[1] for ev in events]
        # 
        # # get values
        # values = eventGroup.values[np.array(indices, dtype=int)]
        # 
        # # times
        # times = [self._timebase.mw_to_audio(ev[2]) for ev in events]
        # return times, values
    
    def get_stimuli(self, matchstr = None, timeRange = None):
        times, values = self.get_events('#stimDisplayUpdate', timeRange)
        for (t, v) in zip(times, values):
            if v is None: logging.warning("Found #stimDisplayUpdate with value = None at %f" % t)
            for i in v:
                if 'bit_code' in i.keys():
                    mwC.append(int(i['bit_code']))
                    mwT.append(t)
        pass
    
    def get_blackouts(self):
        pass
    
    def add_blackout(self, beginning, end):
        pass