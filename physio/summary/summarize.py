#!/usr/bin/env python

import logging

import numpy

import tables

from .. import cfg
from .. import events
from .. import session

def summarize_session(session_name):
    #c = cfg.Config()
    #c.read_user_config()
    #c.set_session(session_name)
    config = cfg.load(session_name)
    n_epochs = session.get_n_epochs(session_name)
    logging.debug("Summarizing %i epochs for session %s" % (n_epochs, session_name))
    for epoch_index in xrange(n_epochs):
        session_object = session.load(session_name, epoch_index)
        fn = '%s/%s/%s_%i.h5' % (config.get('filesystem','resultsrepo'),\
                session_name, session_name, epoch_index)
        logging.debug("Saving summary to %s" % fn)
        summarize_session_object(session_object, fn)


def summarize_session_object(session, output_filename):
    """
    Generate an intermediate representation for a session
    """
    summary_file = tables.openFile(output_filename, 'w')
    
    #gtt, gts, btt, bts = session.get_trials()
    image_times, image_stims = session.get_stimuli()
    rect_times, rect_stims = session.get_stimuli(stimType = 'rectangle')

    stims = events.stimuli.unique(rect_stims + image_stims) # dicts

    # 1) stimuli
    logging.debug("Adding stimuli to summary")
    class StimDescription(tables.IsDescription):
        name = tables.StringCol(32)
        pos_x  = tables.Float64Col()
        pos_y  = tables.Float64Col()
        rotation = tables.Float64Col()
        size_x = tables.Float64Col()
        size_y = tables.Float64Col()
    stim_table = summary_file.createTable('/', 'Stimuli', StimDescription)
    stim_lookup = {}
    
    for (stim_index, stim) in enumerate(stims):
        for key in ['name', 'pos_x', 'pos_y', 'rotation',\
                'size_x', 'size_y']:
            stim_table.row[key] = stim[key]
        stim_table.row.append()
        stim_lookup[events.stimuli.stimhash(stim)] = stim_index
        #stim_lookup.append(events.stimuli.stimhash(stim))
    summary_file.flush()

    # 2) trials [stimulus, duration, outcome]
    logging.debug("Adding trials to summary")
    class TrialDescription(tables.IsDescription):
        stim_index = tables.UInt32Col()
        duration = tables.UInt64Col() # ms
        time = tables.Float64Col()
        outcome = tables.UInt8Col() # 0 success, 1 failure
        # for BlueSquare: 0 = success, 1 = ignore
        # for image: 0 = correctIgnore, 1 = failure
    trial_table = summary_file.createTable('/', 'Trials',\
            TrialDescription)

    tr = session.get_epoch_time_range('mworks')
    tr[0] = 0
    image_duration_times, image_duration_values = \
            session.get_events('Distractor_Time', timeRange = tr)
    rect_duration_times, rect_duration_values = \
            session.get_events('StimulusPresentation_time', timeRange = tr)
    ftimes, _ = session.get_events('failure')
    ftimes = numpy.array(ftimes)
    stimes, _ = session.get_events('success')
    stimes = numpy.array(stimes)
    
    times = rect_times + image_times
    stims = rect_stims + image_stims
    for (time, stim) in zip(times, stims):
        stim_index = stim_lookup[events.stimuli.stimhash(stim)]
        if stim['type'] == 'image':
            duration = 500
            for dt, dv in zip(image_duration_times, image_duration_values):
                if time >= dt:
                    duration = dv
                else:
                    break
            # look for failure
            outcome = 0 # success
            f = ftimes[numpy.logical_and(ftimes > time,\
                    ftimes < (time + duration/1000.))]
            if len(f):
                outcome = 1
        else:
            duration = 1000
            for dt, dv in zip(rect_duration_times, rect_duration_values):
                if time >= dt:
                    duration = dv
                else:
                    break
            # look for 
            outcome = 1 # ignore
            s = stimes[numpy.logical_and(stimes > time,\
                    stimes < (time + duration/1000.))]
            if len(s):
                outcome = 0

        trial_table.row['stim_index'] = stim_index
        trial_table.row['duration'] = duration
        trial_table.row['time'] = time
        trial_table.row['outcome'] = outcome
        trial_table.row.append()
    summary_file.flush()

    # 3) spikes
    logging.debug("Adding spikes to summary")
    class SpikeDescription(tables.IsDescription):
        ch = tables.UInt8Col()
        cl = tables.UInt8Col()
        time = tables.Float64Col()
    spike_table = summary_file.createTable('/', 'Spikes', \
            SpikeDescription)

    #nclusters = {} # TODO save this later

    for ch in xrange(1,33): # tdt numbering
        #nclusters[ch] = session.get_n_clusters(ch)
        #for cl in xrange(nclusters[ch]):
        for cl in xrange(session.get_n_clusters(ch)):
            spike_times = session.get_spike_times(ch, cl)
            for spike_time in spike_times:
                spike_table.row['ch'] = ch
                spike_table.row['cl'] = cl
                spike_table.row['time'] = spike_time
                spike_table.row.append()
    summary_file.flush()

    # find waveform length
    wfs = session._file.root.Channels.ch1.coldtypes['wave'].shape
    # tables for spike ch info (nclusters, signal to noise, etc)
    class SpikeInfoDescription(tables.IsDescription):
        ch = tables.UInt8Col()
        cl = tables.UInt8Col()
        #snr = tables.Float64Col()
        wave_mean = tables.Float64Col(shape=wfs)
        wave_std = tables.Float64Col(shape=wfs)
    spike_info_table = summary_file.createTable('/', 'SpikeInfo', \
            SpikeInfoDescription)

    for ch in xrange(1,33): # tdt numbering
        for cl in xrange(session.get_n_clusters(ch)):
            waves = numpy.array(session.get_spike_waveforms(ch, cl))
            if len(waves) == 0: continue
            wave_mean = numpy.mean(waves, 0)
            wave_std = numpy.std(waves, 0)
            spike_info_table.row['ch'] = ch
            spike_info_table.row['cl'] = cl
            spike_info_table.row['wave_mean'] = wave_mean
            spike_info_table.row['wave_std'] = wave_std
            spike_info_table.row.append()
    summary_file.flush()

    # 4) gaze
    logging.debug("Adding gaze to summary")
    tt, tv, hv, vv, pv = session.get_gaze()
    class GazeDescription(tables.IsDescription):
        time = tables.Float64Col()
        h = tables.Float64Col()
        v = tables.Float64Col()
        pupil_radius = tables.Float64Col()
        cobra_timestamp = tables.Float64Col()
    gaze_table = summary_file.createTable('/', 'Gaze', \
            GazeDescription)
    for i in xrange(len(tt)):
        # TODO handle inf/nan ?
        gaze_table.row['time'] = tt[i]
        gaze_table.row['cobra_timestamp'] = tv[i]
        gaze_table.row['h'] = hv[i]
        gaze_table.row['v'] = vv[i]
        gaze_table.row['pupil_radius'] = pv[i]
        gaze_table.row.append()

    #gaze_group = summary_file.createGroup('/', 'Gaze', 'Gaze')
    #summary_file.createArray(gaze_group, 'times', tt)
    #summary_file.createArray(gaze_group, 'cobra_timestamps', tv)
    #summary_file.createArray(gaze_group, 'gaze_h', hv)
    #summary_file.createArray(gaze_group, 'gaze_v', vv)
    #summary_file.createArray(gaze_group, 'pupil_radius', pv)
    #summary_file.flush()

    # 5) location
    logging.debug("Adding locations to summary")
    locs = session.get_channel_locations()
    class LocationDescription(tables.IsDescription):
        ml = tables.Float64Col()
        ap = tables.Float64Col()
        dv = tables.Float64Col()
    location_table = summary_file.createTable('/', 'Locations',\
            LocationDescription)
    for loc in locs:
        location_table.row['ml'] = loc[0]
        location_table.row['ap'] = loc[1]
        location_table.row['dv'] = loc[2]
        location_table.row.append()
    summary_file.flush()

    # TODO  Meta information (session data, probe data, epoch, etc...)
    logging.debug("Adding meta info to summary")
    # physio version TODO how do I do this?
    #version = __version__
    #logging.debug("Found version %s" % version)

    # datafile md5sum
    md5sum = session.get_md5sum()
    logging.debug("Found md5sum %s" % str(md5sum))
    summary_file.root._v_attrs['src_md5'] = md5sum

    # epoch time range
    au_time_range = session.get_epoch_time_range('au')
    summary_file.root._v_attrs['au_start'] = au_time_range[0]
    summary_file.root._v_attrs['au_end'] = au_time_range[1]

    summary_file.close()
