import scikits.audiolab as al
import os
import subprocess
import shlex
#import matplotlib.pylab as plt
from numpy import *
import re
from copy import copy
from sox_utils import sox_merge
import mworks.data as mw

def sox_process_pixel_clock(project_path, file_no,  out_path, out_filename, **kwargs):
    return sox_merge("pixel_clock", file_no, project_path, out_path, out_filename, **kwargs)


def read_pixel_clock( project_path, cache_dir, file_no, **kwargs):
    
    time_range = kwargs.get('time_range', None)
    
    pc_filename = "pixel_clock_merged_%d.wav" % file_no
    pc_merged_file_path = os.path.join(cache_dir, pc_filename)
    
    # if the file doesn't exist in the cache, try to build it
    if not os.path.exists(pc_merged_file_path ):
        sox_process_pixel_clock( project_path, file_no, cache_dir, pc_filename,
                                 norm=True,
                                 highpass=100,
                                 time_range=time_range)
    
    (pc_data, fs, fmt) = al.wavread(pc_merged_file_path)
    
    #return (diff(pc_data,1,0), fs)
    return (pc_data, fs)

def state_to_code(state):
    
    code = 0
    for i in range(0, len(state)):
        code += 2**i * state[i]
    return code

def reconstruct_codes( events, n_channels, raise_on_inconsistency=False,
                                           channel_mask=None):

    if channel_mask is None:
        channel_mask = [1] * n_channels
        
    start_state = [None] * n_channels

    # read through the  events until a change is found on every channel
    # the change direction tells us the state *before* the change
    for e in events:
        state = e[1]
        for c in range(0, n_channels):
            if start_state[c] is None and state[c] is not 0:
                # remap -1/1 to 0/1
                start_state[c] = (-state[c]*channel_mask[c] + 1) / 2

        if not (None in start_state):
            break
    if None in start_state:
        print("something went wrong, setting start state to zeros")
        start_state = [0,0,0,0]
    else:
        print("start state is inferred to be: %s" % start_state)

    # now we can sequentially reconstruct the codes
    previous_state = start_state
    current_state = [None] * n_channels
    for e in events:
        state_change = e[1]
        for c in range(0, n_channels):
            current_state[c] = previous_state[c] + state_change[c]
            if current_state[c] < 0 or current_state[c] > 1:
                if raise_on_inconsistency:
                    print "Funky: %s" % current_state
                    raise Exception("Inconsistent pixel clock sequence")
                else:
                    print "FUNKY!: %s" % current_state
                current_state[c] = min( current_state[c], 1 )
                current_state[c] = max( current_state[c], 0 )
                
        #print "%s + %s = %s (%f)" % (previous_state, state_change, 
        #                             current_state, e[0])
        
        previous_state = copy(current_state)
        
        e[2] = state_to_code(current_state) 

    return events


def code_to_mask( num, n_channels ):
    
    mask = [None] * n_channels
    for i in range(0, n_channels):
        if (num & 2**i) != 0:
            mask[i] = 1
        else:
            mask[i] = -1
    
    return mask

def reconstruct_codes_exhaustive_masks( events, n_channels ):
    
    masks_to_try = [code_to_mask(c,n_channels) for c in range(0,2**n_channels)]

    successful_mask = None
    new_events = None
    
    for mask in masks_to_try:
        print("Trying mask: %s" % mask)
        try:
            new_events = copy(events)
            new_events = reconstruct_codes( new_events, n_channels,
                                            True, mask)
        except:
            continue
        
        successful_mask = mask
        print("Successful mask = %s" % mask)
        break
    
    return (new_events, successful_mask)
        
        

def parse_pixel_clock(pc_data, start_time_sec, samples_per_sec, **kwargs):
    
    samples_per_sec = float(samples_per_sec)
    
    arm_threshold = kwargs.get("arm_threshold", 0.1)
    arm_timeout = kwargs.get("arm_timeout", 0.005) * samples_per_sec
    accept_threshold = kwargs.get("accept_threshold", 0.3)
    time_stride = int(kwargs.get("time_stride", 0.0005) * samples_per_sec)
    refractory_period = int(kwargs.get("refractory_period", 0.010) * samples_per_sec)
    event_trigger_period = int(kwargs.get("event_trigger_period", 0.05) * samples_per_sec)
    
    print refractory_period
    
    # TODO: check the data to make sure format is okay
    
    out_codes = []
    
    n_channels = pc_data.shape[1]
    n_timepoints = pc_data.shape[0]
    
    # assume the start state is all zeros to begin with
    state = [0] * n_channels
    armed = [False] * n_channels
    event_triggered = False
    event_trigger_window = 0
    armed_index = [None] * n_channels
    refractory = [False] * n_channels
    
    
    print pc_data.shape
    
    # iterate through the data file
    for t in range(0, n_timepoints, time_stride):
        # if t % 100000 == 0:
        #   print "Processing time point %d" % t
        
        for c in range(0, n_channels):
            
            datum = pc_data[t, c]
            
            if not event_triggered:
            
                # if armed, we're looking for an event trigger
                if armed[c]:    
                    
                    # if too much time has passed, disarm
                    if (t - armed_index[c]) > arm_timeout:
                        armed[c] = False
                        armed_index[c] = None
                        #print("arm timeout: %f" % (t / float(samples_per_sec)))
                              
                    # check to see if we've crossed the "accept" threshold
                    elif abs(datum) > accept_threshold:
                        # "trigger" event
                        state = [0] * n_channels
                        event_triggered = True
                        event_trigger_window = event_trigger_period
                        event_index = armed_index[c]
                        #print("Event triggered on channel %d" % c)
                    
                        # "disarm"
                        armed = [False] * n_channels
                        armed_index = [None] * n_channels
                    
                    
                # if not armed, check if we should be
                else:
                    # check if we should "arm" based on this data
                    if abs(datum) > arm_threshold:
                        armed[c] = True
                        armed_index[c] = t
                        #print("Armed at %d on channel %d" % (armed_index[c],c) )
            
            # if an event is triggered, adjust the state
            if event_triggered:
                if refractory[c]:
                    # check if we've returned to the arm threshold
                    if abs(datum) <= arm_threshold:
                        refractory[c] = False
                    else:
                        continue
                if datum > accept_threshold:
                    state[c] = 1
                    refractory[c] = True
                elif datum < -accept_threshold:
                    # TODO: check if we need to revise the previous code
                    state[c] = -1
                    refractory[c] = True
        


        if event_triggered and not (True in refractory):
            event_time = start_time_sec + (event_index / samples_per_sec )
            out_codes.append( [ event_time, state, None ])
            #print("%f (%d): %s" % (event_time, event_index, state))
            event_triggered = False
            
    out_codes = reconstruct_codes(out_codes, n_channels)
    # (out_codes, mask) = reconstruct_codes_exhaustive_masks(out_codes, 
    #                                                       n_channels)
    
    return out_codes


def read_pixel_clock_from_mw(mw_filename, use_display_update=False):

    f = mw.MWKFile(mw_filename)
    f.open()
    
    if use_display_update:
        pc_events = f.get_events(codes=["#stimDisplayUpdate"])
        
        def get_pc_from_evt(e):
            try:
                stimuli = e.value
                for s in stimuli:
                    if s.has_key('bit_code'):
                        return s['bit_code']
            except:
                return None
            return None
        
        def is_pc_update_evt(e):
            return ( get_pc_from_evt(e) is not None )
        
        pc_evts = filter(is_pc_update_evt, pc_events)
        codes = [get_pc_from_evt(e) for e in pc_evts]
        times = [ e.time for e in pc_evts ]
    else:
        pc_events = f.get_events(codes=["#pixelClockCode"])
        times = [ e.time for e in pc_events ]
        codes = [ e.value for e in pc_events ]

    f.close()
    
    # float_times = [ (t - times[0]) / 1.e6 for t in times ]
    float_times = [ t / 1.e6 for t in times ]
    
    return (float_times, codes)
 
# determine the offset between pixel clock and mw stream
# the resulting number should be subtracted from mw times 
# or added to the logic / caton times
def time_match_mw_with_pc(pc_codes, pc_times, mw_codes, mw_times,
                                submatch_size = 10, slack = 0, max_slack=10,
                                pc_check_stride = 100):
    
    time_matches = []
    
    for pc_start_index in range(0, len(pc_codes)-submatch_size, pc_check_stride):
        match_sequence = pc_codes[pc_start_index:pc_start_index+submatch_size]
        pc_time = pc_times[pc_start_index]
        
        for i in range(0, len(mw_codes) - submatch_size - max_slack):
            good_flag = True
                
            total_slack = 0
            for j in range(0, submatch_size):
                target = match_sequence[j]
                if target != mw_codes[i+j+total_slack]:
                    slack_match = False
                    slack_count = 0
                    while slack_count < slack and j != 0:
                        slack_count += 1
                        total_slack += 1
                        if target == mw_codes[i+j+total_slack]:
                            slack_match = True
                            break
                
                    if total_slack > max_slack:
                        good_flag = False
                        break
                    
                    if not slack_match:
                        # didn't find a match within slack
                        good_flag = False
                        break
                    
            if good_flag:
                print "Total slack: %d" % total_slack
                print "%s matched to %s" % (match_sequence, mw_codes[i:i+submatch_size+total_slack])
                time_matches.append((pc_time, mw_times[i]))
                break
    
    return time_matches
    
if __name__ == "__main__":
    
    import sys
    import matplotlib.pylab as plt
    project_path = sys.argv[1]
    cache_dir = "/tmp/phys"

    print("Reading in data...")
    (pc_data, fs) = read_pixel_clock( project_path, cache_dir, 1 , time_range=(0,1200))
    
    print("Parsing data...")
    events = parse_pixel_clock( pc_data, 0.0, fs)
    
    
    print("Plotting...")
    min_range = 0
    max_range = -1
    #min_range = 300000
    #max_range = min_range + 300000
    stride = 500
    x = arange(0, pc_data.shape[0] / float(fs), stride / float(fs))
    plt.hold(True)
    plt.plot(x, pc_data[min_range:max_range:stride, 0])
    plt.plot(x, pc_data[min_range:max_range:stride, 1])
    plt.plot(x, pc_data[min_range:max_range:stride, 2])
    plt.plot(x, pc_data[min_range:max_range:stride, 3])

    plt.plot([x[0],x[-1]], [0.05]*2, '--')
    plt.plot([x[0],x[-1]], [-0.05]*2, '--')
    
    plt.plot([x[0],x[-1]], [0.1]*2, '--')
    plt.plot([x[0],x[-1]], [-0.1]*2, '--')
    
    text_level = 0.5
    for e in events:
        plt.text(e[0], text_level, str(e[2]))
    
    plt.show()
    
    print(events)
