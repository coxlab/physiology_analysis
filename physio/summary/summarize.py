#!/usr/bin/env python

import tables

from .. import events

def summarize_session(session, output_filename):
    """
    Generate an intermediate representation for a session
    """
    summary_file = tables.openFile(output_filename, 'w')
    
    gtt, gts, btt, bts = session.get_trials() # no bluesquare for now

    # 1) stimuli
    stims = events.stimuli.unique(gts + bts) # dicts
    class StimDescription(tables.IsDescription):
        name = tables.StringCol(32)
        pos_x  = tables.Float64Col()
        pos_y  = tables.Float64Col()
        rotation = tables.Float64Col()
        size_x = tables.Float64Col()
        size_y = tables.Float64Col()
    stim_table = summary_file.createTable('/', 'Stimuli', StimDescription)
    stim_lookup = []

    for stim in stims:
        for key in ['name', 'pos_x', 'pos_y', 'rotation',\
                'size_x', 'size_y']:
            stim_table.row[key] = stim[key]
        stim_table.row.append()
        stim_lookup.append(events.stimuli.stimhash(stim))
    summary_file.flush()

    # 2) trials [stimulus, duration, outcome]
    tr = session.get_epoch_time_range('mworks')
    tr[0] = 0
    dtts, dtvs = session.get_events('Distractor_Time', timeRange = tr)
    class TrialDescription(tables.IsDescription):
        stim_index = tables.UInt32Col()
        duration = tables.UInt64Col() # ms
        time = tables.Float64Col()
        outcome = tables.UInt8Col() # 0 success, 1 failure
    trial_table = summary_file.createTable('/', 'Trials',\
            TrialDescription)

    for (time, stim) in zip(gtt, gts): # successes
        hash = events.stimuli.stimhash(stim)
        stim_index = stim_lookup.index(hash)
        trial_table.row['stim_index'] = stim_index
        duration = 500 # ms
        for dt in dtts:
            if time >= dt:
                duration = dt
            else:
                break
        trial_table.row['duration'] = duration
        trial_table.row['time'] = time
        trial_table.row['outcome'] = 0
    summary_file.flush()

    for (time, stim) in zip(btt, bts): # failures
        hash = events.stimuli.stimhash(stim)
        stim_index = stim_lookup.index(hash)
        trial_table.row['stim_index'] = stim_index
        duration = 500 # ms
        for dt in dtts:
            if time >= dt:
                duration = dt
            else:
                break
        trial_table.row['duration'] = duration
        trial_table.row['time'] = time
        trial_table.row['outcome'] = 1
    summary_file.flush()

    # 3) spikes
    class SpikeDescription(tables.isDescription):
        ch = tables.UInt8Col()
        cl = tables.UInt8Col()
        time = tables.Float64Col()
    spike_table = summary_file.creatTable('/', 'Spikes', \
            SpikeDescription)

    for ch in xrange(1,33):
        for cl in session.get_n_clusters(ch):
            spike_times = session.get_spike_times(ch, cl)
            for spike_time in spike_times:
                spike_table.row['ch'] = ch
                spike_table.row['cl'] = cl
                spike_table.row['time'] = spike_time
                spike_table.row.append()
    summary_file.flush()

    # 4) gaze
    tt, tv, hv, vv, pv = session.get_gaze()
    gaze_group = summary_file.createGroup('/', 'Gaze', 'Gaze')
    summary_file.createArray(gaze_group, 'times', tt)
    summary_file.createArray(gaze_group, 'cobra_timestamps', tv)
    summary_file.createArray(gaze_group, 'gaze_h', hv)
    summary_file.createArray(gaze_group, 'gaze_v', vv)
    summary_file.createArray(gaze_group, 'pupil_radius', pv)
    summary_file.flush()

    # 5) location
    locs = session.get_channel_locations()
    class LocationDescription(tables.isDescription):
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

    summary_file.close()
