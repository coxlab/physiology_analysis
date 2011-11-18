#!/usr/bin/env python

# import itertools, glob, sys
import glob, os

import numpy as np
# import pylab as pl
import tables

# import pywaveclus

import cfg
import clock
import events
import h5
import utils

def get_n_epochs(config):
    return len(get_epochs(config))

def get_epochs(config):
    mainDir = config.get('session','outputprefix')
    epochs = sorted([os.path.basename(ed) for ed in utils.regex_glob(mainDir, r'^\d+_\d+/?$')[0]],\
        key = lambda s: int(s.split('_')[0]))
    return epochs

def get_epoch_dir(config, number):
    epoch = get_epochs(config)[number]
    return '/'.join((config.get('session','outputprefix'), epoch))

def load(session, epochNumber = 0, config = None):
    if config is None:
        config = cfg.load(session)
    
    # find results file for epoch number
    epochDir = get_epoch_dir(config, epochNumber)
    # epoch = get_epochs(config)[epochNumber]
    # epochDir = '/'.join((config.get('session','outputprefix'), epoch))
    h5files = glob.glob(epochDir+'/*.h5')
    if len(h5files) != 1: utils.error('More than one .h5 file found in output directory: %s' % str(h5files))
    return Session(h5files[0], config.getint('audio','samprate'))
    # 
    # outputDir = config.get('session','output')
    # h5files = glob.glob(outputDir+'/*.h5')
    # if len(h5files) != 1: utils.error('More than one .h5 file found in output directory: %s' % str(h5files))
    # return Session(h5files[0], config.getint('audio','samprate'))

class Session(object):
    """
    Times are always provided in seconds since beginning of epoch in audio units
    """
    def __init__(self, h5filename, samplingrate = 44100):
        self._file = tables.openFile(h5filename,'r')
        self._filename = h5filename
        
        self._samplingrate = samplingrate
        self.read_timebase()
    
    def read_timebase(self):
        matchesNode = self._file.getNode('/TimeMatches')
        self._timebase = clock.timebase.TimeBase(np.array(matchesNode), fitline=False)#fitline=True)
        #austart = self._file.root._v_attrs['EPOCH_START_AUDIO']
        #matches = np.array(matchesNode)
        #matches[:,0] = matches[:,0] + austart
        #self._timebase = clock.timebase.TimeBase(matches, fitline=False)
    
    def get_epoch_time_range(self, unit):
        """
        Parameters
        ----------
        unit : string
            Either mworks, mw, audio, or au
        
        Returns
        -------
        beginning : float
            Time at beginning of epoch
        end : float
            Time at end of epoch
        
        Notes
        -----
        There are two time units (audio and mworks)
            mworks times are always relative to the start of mworks
            audio times are relative to the start of the epoch
        """
        
        au_session = [self._file.root._v_attrs['EPOCH_START_AUDIO'], self._file.root._v_attrs['EPOCH_END_AUDIO']]
        #au_epoch = [0, au_session[1] - au_session[0]]
        au_epoch = [au_session[0], au_session[1]]
        if unit[:2] == 'au':
            return au_epoch
        elif unit[:2] == 'mw':
            mw_epoch = [self._timebase.audio_to_mworks(au_epoch[0]), self._timebase.audio_to_mworks(au_epoch[1])]
            return mw_epoch
        else:
            utils.error("Unknown time unit[%s]" % unit)
    
    def close(self):
        self._file.close()
    
    def get_n_clusters(self, channel):
        n = self._file.getNode('/Channels/ch%i' % channel)
        clus = np.array([r['clu'] for r in n])
        if len(clus) == 0: return 0
        maxI = clus.max()
        return maxI + 1
    
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
        if timeRange is None:
            timeRange = self.get_epoch_time_range('mworks')
        
        times, values = h5.events.get_events(self._file, name, timeRange)
        autimes = [self._timebase.mworks_to_audio(t) for t in times]
        return autimes, values
    
    def get_codec(self):
        return h5.events.get_codec(self._file)
    
    def get_stimuli(self, matchDict = None, timeRange = None, stimType = 'image'):
        """
        Does not look for 'failed' trials
        """
        if timeRange is None:
            timeRange = self.get_epoch_time_range('mworks')
        
        times, stims = events.stimuli.get_stimuli(self._file, timeRange, stimType)
        if not (matchDict is None):
            times, stims = events.stimuli.match(times, stims, matchDict)
        autimes = [self._timebase.mworks_to_audio(t) for t in times]
        return autimes, stims
    
    def get_trials(self, matchDict = None, timeRange = None):
        times, stims = self.get_stimuli(matchDict, timeRange)
        tr = self.get_epoch_time_range('mworks')
        tr[0] = 0
        dtts, dtvs = self.get_events('Distractor_Time', timeRange = tr)
        dtts = np.array(dtts)
        # if len(dtt) != 1: utils.error("Cannot handle sessions where distractor presentation time changed")
        # presentationTime = dtv[0] / 1000.
        
        ftimes, _ = self.get_events('failure')
        
        goodTimes = []
        goodStims = []
        badTimes = []
        badStims = []
        for (t,s) in zip(times, stims):
            # find distractor time
            di = np.where(dtts < t)[0][-1] # index of current distractor time
            # dt = dtts[di]
            pt = dtvs[di] / 1000. # convert to seconds
            if any(((ftimes - t) > 0) & ((ftimes - t) < pt)):
                # failed trial
                badTimes.append(t)
                badStims.append(s)
            else:
                # good trial
                goodTimes.append(t)
                goodStims.append(s)
        return goodTimes, goodStims, badTimes, badStims
    
    def get_channel_locations(self):
        cncDict = events.cnc.get_cnc_events(self._file)
        offset = events.cnc.get_tip_offset(self._file)
        time, _ = self.get_epoch_time_range('mworks')
        return events.cnc.get_channel_locations(cncDict, offset, time)
    
    def get_gaze(self, start=1, timeRange=None):
        """
        Parameters
        ----------
            start : datapoint index to start processing gaze data
                sample 0 tends to be an error, so this is by default 1
        Returns
        -------
            tt : audio times of culled gaze data points
            tv : cobra timestamps
            hv : horizontal gaze
            vv : vertical gaze
            pv : pupil radius
        """
        ht, hv = self.get_events('gaze_h', timeRange)
        vt, vv = self.get_events('gaze_v', timeRange)
        pt, pv = self.get_events('pupil_radius', timeRange)
        tt, tv = self.get_events('cobra_timestamp', timeRange)
        # find indices of 'good' data points, ones that don't deviate too far from the mean
        good = events.gaze.find_good_by_deviation(hv[start:], vv[start:])
        if len(good) == 0:
            return [], [], [], [], []
        else:
            return np.array(tt)[good+1], np.array(tv)[good+1], np.array(hv)[good+1], np.array(vv)[good+1], np.array(pv)[good+1]
    
    def get_blackouts(self):
        pass
    
    def add_blackout(self, beginning, end):
        pass
