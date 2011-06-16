import scikits.audiolab as al
import os
import subprocess
import shlex
#import matplotlib.pylab as plt
import numpy as np
import re
from copy import copy, deepcopy
from sox_utils import sox_merge
import mworks.data as mw
import logging


class PixelClockEvt:
    """ 
    A simple container for storing pixel clock events 
    """
    
    def __init__(self, evt_time, trigger_channel=None, state=None, code=None):
        self.time = evt_time
        self.trigger_channel = trigger_channel
        self.state = state
        self.code = code

    def __lt__(self, evt):
        return self.time < evt.time
        
    def __repr__(self):
        t = self.time
        c = self.trigger_channel
        s = self.state
        code = self.code
        
        if code is None:
            code = -1
            
        return "{ %f: ch%d %s: %d }  " % (t,c,s,code) 


class TimeBase:
    
    def __init__(self, evt_zipper, audio_offset = 0):
        
        # evt_zipper is a list of tuples containing pc_time -> mw_time
        self.evt_zipper = deepcopy(evt_zipper)
        self.evt_zipper.sort()
        
        # offset: pc_time - mw_t
        # to convert:
        #   pc_time -> mw_time:  pc_time - offset
        #   mw_time -> pc_time:  mw_time + offset
        self.mw_offsets = np.array([ e[0] - e[1] for e in evt_zipper ]) - \
                          audio_offset
        
        # this is the offset of the file used to make the zipper, if any
        self.audio_offset = audio_offset
        if self.audio_offset != 0:
            logging.error("setting audio_offset which is Not implemented")
    
    
    def mw_time_to_audio(self, mw_time, mw_offset = 0):
        
        mw_t = mw_time + mw_offset
        # print mw_t
        for (i, evt_match) in enumerate(self.evt_zipper):
            # print evt_match
            # if mw_t > evt_match[1]:
            if evt_match[1] >= mw_t:
                # simple "one point" matching for now
                return mw_t + self.mw_offsets[i]
        
        logging.warning("mw_time_to_audio matched to last offset")
        return mw_t + self.mw_offsets[-1]

    def audio_time_to_mw(self, audio_time, audio_offset = 0):
        
        a_t = audio_time + audio_offset
        
        for (i, evt_match) in enumerate(self.evt_zipper):
            # if a_t > evt_match[0]:
            if evt_match[0] >= a_t:
                return a_t - self.mw_offsets[i]
        
        logging.warning("audio_time_to_mw matched to last offset")
        return a_t - self.mw_offsets[-1]

def sox_process_pixel_clock(project_path, file_no,  out_path, out_filename, 
                            **kwargs):
    return sox_merge("pixel_clock", file_no, project_path, out_path, 
                     out_filename, **kwargs)


def read_pixel_clock( project_path, file_no, cache_dir="/tmp", time_range=None):
    
    
    pc_file_stem = "pixel_clock_merged_session_%d" % file_no
    if time_range is not None:
        pc_file_stem += "_%d_to_%d" % (time_range[0], time_range[1])
        
    pc_filename = pc_file_stem + ".wav"
    pc_merged_file_path = os.path.join(cache_dir, pc_filename)
    
    # if the file doesn't exist in the cache, try to build it
    if not os.path.exists(pc_merged_file_path ):
        sox_process_pixel_clock( project_path, file_no, cache_dir, pc_filename,
                                 norm=True,
                                 highpass=200,
                                 time_range=time_range)
    
    (pc_data, fs, fmt) = al.wavread(pc_merged_file_path)
    
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
        state = e.state
        for c in range(0, n_channels):
            if start_state[c] is None and state[c] is not 0:
                # remap -1/1 to 0/1
                start_state[c] = (-state[c]*channel_mask[c] + 1) / 2

        if not (None in start_state):
            break
    if None in start_state:
        logging.warning("something went wrong, setting start state to zeros")
        start_state = [0,0,0,0]
    else:
        logging.debug("start state is inferred to be: %s" % start_state)

    # now we can sequentially reconstruct the codes
    previous_state = start_state
    current_state = [None] * n_channels
    inconsistencies_found = False
    for e in events:
        state_change = e.state
        for c in range(0, n_channels):
            current_state[c] = previous_state[c] + state_change[c]
            if current_state[c] < 0 or current_state[c] > 1:
                if raise_on_inconsistency:
                    raise Exception("Inconsistent pixel clock sequence")
                else:
                    inconsistencies_found = True
                current_state[c] = min( current_state[c], 1 )
                current_state[c] = max( current_state[c], 0 )
                
        
        previous_state = copy(current_state)
        
        e.code = state_to_code(current_state) 

    if inconsistencies_found:
        logging.warning("Inconsistent pixel clock sequences were found")
    return events  # [time, [state0, state[1]...], presumed_code]


def code_to_mask( num, n_channels ):
    
    mask = [None] * n_channels
    for i in range(0, n_channels):
        if (num & 2**i) != 0:
            mask[i] = 1
        else:
            mask[i] = -1
    
    return mask


        

# def parse_pixel_clock(pc_data, start_time_sec, samples_per_sec,
#                       arm_threshold = 0.1, arm_timeout = 0.005, 
#                       accept_threshold = 0.3,
#                       time_stride=0.0005, refractory_period = 0.010,
#                       event_trigger_period = 0.05):
#     
#     samples_per_sec = float(samples_per_sec)
#     
#     arm_timeout *= samples_per_sec
#     time_stride = int(time_stride * samples_per_sec)
#     refractory_period = int(refractory_period * samples_per_sec)
#     event_trigger_period = int(event_trigger_period* samples_per_sec)
#     
#     print refractory_period
#     
#     # TODO: check the data to make sure format is okay
#     
#     # where we'll store parsed events
#     evts = []
#     
#     n_channels = pc_data.shape[1]
#     n_timepoints = pc_data.shape[0]
#     
#     # assume the start state is all zeros to begin with
#     state = [0] * n_channels
#     armed = [False] * n_channels
#     event_triggered = False
#     event_trigger_window = 0
#     armed_index = [None] * n_channels
#     refractory = [False] * n_channels
#     
#     
#     print pc_data.shape
#     
#     # iterate through the data file
#     for t in range(0, n_timepoints, time_stride):
#         # if t % 100000 == 0:
#         #   print "Processing time point %d" % t
#         
#         for c in range(0, n_channels):
#             
#             datum = pc_data[t, c]
#             
#             if not event_triggered:
#             
#                 # if armed, we're looking for an event trigger
#                 if armed[c]:    
#                     
#                     # if too much time has passed, disarm
#                     if (t - armed_index[c]) > arm_timeout:
#                         armed[c] = False
#                         armed_index[c] = None
#                         #print("arm timeout: %f" % (t / float(samples_per_sec)))
#                               
#                     # check to see if we've crossed the "accept" threshold
#                     elif abs(datum) > accept_threshold:
#                         # "trigger" event
#                         state = [0] * n_channels
#                         event_triggered = True
#                         event_trigger_window = event_trigger_period
#                         
#                         # set the event time to the last "arm" time
#                         event_index = armed_index[c]
#                         
#                         # "disarm" (because event is triggered)
#                         armed = [False] * n_channels
#                         armed_index = [None] * n_channels
#                     
#                     
#                 # if not armed, check if we should be
#                 else:
#                     
#                     if abs(datum) > arm_threshold:
#                         armed[c] = True
#                         
#                         # save the time index of the this "arming".
#                         # this will be the event time, should an evt be 
#                         # triggered
#                         armed_index[c] = t
#                         
#             
#             # if an event is triggered, adjust the state
#             if event_triggered:
#                 if refractory[c]:
#                     # if already in a triggered event
#                     # check if we've returned to the arm threshold (indicating
#                     # an end of this event)
#                     if abs(datum) <= arm_threshold:
#                         refractory[c] = False
#                     else:
#                         continue
#                 if datum > accept_threshold:
#                     state[c] = 1
#                     refractory[c] = True
#                 elif datum < -accept_threshold:
#                     state[c] = -1
#                     refractory[c] = True
#         
# 
#         
#         if event_triggered and not (True in refractory):
#             event_time = start_time_sec + (event_index / samples_per_sec )
#             new_evt = PixelClockEvt(event_time, trigger_channel=c, 
#                                     state=state)
#             evts.append(new_evt)
#             event_triggered = False
#             
#     evts = reconstruct_codes(evts, n_channels)
#     
#     return evts



def parse_pixel_clock(pc_data, start_time_sec, samples_per_sec,
                      arm_threshold = 0.1, arm_timeout = 0.005, 
                      accept_threshold = 0.3, derivative_threshold = 0.0,
                      time_stride=0.0005, refractory_period = 0.010,
                      event_trigger_period = 0.05,
                      pc_y_pos_deg = None,
                      pc_height_deg = None,
                      screen_height_deg = None):

    samples_per_sec = float(samples_per_sec)
    arm_timeout *= samples_per_sec
    time_stride_samples = int(time_stride * samples_per_sec)
    refractory_samples = int(refractory_period * samples_per_sec)
    event_trigger_period = int(event_trigger_period* samples_per_sec)

    min_delta = derivative_threshold * time_stride

    # TODO: check the data to make sure format is okay

    out_codes = []

    n_channels = pc_data.shape[1]
    n_timepoints = pc_data.shape[0]

    events_by_channel = [ [] for x in range(0,n_channels) ]

    # iterate through the data file, one channel at a time
    for c in range(0, n_channels):
        
        event_triggered = False
        event_trigger_window = 0
        armed_index = None
        refractory = False
        state = None
        armed = False
        
        for t in range(0, n_timepoints, time_stride_samples):
        
            datum = pc_data[t, c]
            
            if t > 0:
                last_datum = pc_data[t-1,c]
                delta = datum - last_datum
            else:
                last_datum = 0
                delta = 0
            
            
            
            if not event_triggered:

                # if armed, we're looking for an event trigger
                if armed:    

                    # if too much time has passed, disarm
                    if abs(datum) < arm_threshold:
                        armed = False
                        armed_index = None

                    # check to see if we've crossed the "accept" threshold
                    elif abs(datum) > accept_threshold and \
                             np.sign(delta) == np.sign(datum) and \
                             abs(delta) > min_delta:
                        # "trigger" event
                        if datum > 0:
                            state = 1
                        else:
                            state = -1
                        
                        event_triggered = True
                        event_trigger_window = event_trigger_period

                        # set the event time to the last "arm" time
                        event_index = armed_index

                        refractory = True
                        
                        # "disarm" (because event is triggered)
                        armed = False
                        armed_index


                # if not armed, check if we should be
                else:

                    if abs(datum) > arm_threshold:
                        armed = True

                        # save the time index of the this "arming".
                        # this will be the event time, should an evt be 
                        # triggered
                        armed_index = t


            # if an event is triggered, adjust the state
            if event_triggered:
                if refractory:
                    # if already in a triggered event
                    # check if we've returned to the arm threshold (indicating
                    # an end of this event)
                    #if (t - event_index) > refractory_samples and \
                    if np.sign(delta) == -1 * np.sign(last_datum) and \
                                    abs(datum) <= accept_threshold:
                       refractory = False
                    else:
                        continue
                # if datum > accept_threshold:
                #                     state = 1
                #                     refractory[c] = True
                #                 elif datum < -accept_threshold:
                #                     state[c] = -1
                #                     refractory[c] = True



            if event_triggered and not refractory:
                event_time = start_time_sec + (event_index / samples_per_sec )
                evt = PixelClockEvt(event_time, trigger_channel=c, state=state)
                events_by_channel[c].append(evt)
                event_triggered = False


    all_events = []
    for c in range(0, n_channels):
        all_events += events_by_channel[c]

    # sort by the evt time
    all_events.sort() 
    
    
    # TODO: reconstruct unified events from the stream of per channel events
    consolidated_events = []
    last_time = -np.Inf
    current_event = None
    last_channel = None
    start_of_evt_channel = None
    
    # A matrix to store channel-to-channel latency information (n x n [])
    channel_range = range(0, n_channels)
    latencies = [ [ [] for x in channel_range ] for y in channel_range ]
    
    for (i,e) in enumerate(all_events):
        current_channel = e.trigger_channel
        direction = e.state 
        
        if (e.time - last_time) > refractory_period or current_event is None:
            # create new event
            new_event = PixelClockEvt(e.time, 
                                     trigger_channel=current_channel,
                                     state = [0]*n_channels )
            new_event.state[current_channel] = direction
            start_of_evt_channel = current_channel
            
            # store the last event
            if current_event is not None:
                consolidated_events.append(current_event)
            
            current_event = new_event
            last_time = e.time
        
        else:
            # add to last event
            current_event.state[current_channel] = direction
            
            # compute channel time offset relative to the channel that triggered
            time_diff = e.time - current_event.time
            
            # store channel-to-channel latency info
            latencies[start_of_evt_channel][current_channel].append(time_diff)
            latencies[current_channel][start_of_evt_channel].append(-time_diff) 
    
    
    avg_latencies = np.zeros((n_channels, n_channels))
    for c1 in range(0, n_channels):
        for c2 in range(0, n_channels):
            avg_latencies[c1,c2] = np.mean(latencies[c1][c2])
    
    offset_latencies = np.zeros((n_channels,))
    for c in range(1, n_channels):
        offset_latencies[c] = avg_latencies[0, c]
    
    # set latencies relative to center
    offset_latencies -= np.mean(offset_latencies)
    
    if pc_y_pos_deg is not None and pc_height_deg is not None and \
       screen_height_deg is not None:
       
       pc_time_span = (offset_latencies[-1] - offset_latencies[0])
       degs_per_sec = pc_height_deg / pc_time_span
       screen_halfheight = screen_height_deg / 2.
       
       # pc_y_pos_deg assumed to be negative
       pc_offset_from_bottom_deg = screen_halfheight + pc_y_pos_deg
       
       pc_offset_from_bottom_sec = pc_offset_from_bottom_deg / degs_per_sec
       
       offset_latencies += pc_offset_from_bottom_sec
    
    # correct for offsets latencies
    for e in consolidated_events:
        e.time += offset_latencies[e.trigger_channel]
    
    # reconstruct binary codes from state transitions
    reconstructed_events = reconstruct_codes(consolidated_events, n_channels)
    
    # [time, [state0, state[1]...], presumed_code]
    return reconstructed_events, offset_latencies


def read_pixel_clock_from_mw(mw_filename, use_display_update=True):

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
# the return value is a list of time match tuples (audio_time, mw_time)

def time_match_mw_with_pc(pc_codes, pc_times, mw_codes, mw_times,
                                submatch_size = 10, slack = 0, max_slack=10,
                                pc_check_stride = 100, pc_file_offset= 0):
    
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
                logging.info("Total slack: %d" % total_slack)
                logging.info("%s matched to %s" % \
                      (match_sequence, mw_codes[i:i+submatch_size+total_slack]))
                time_matches.append((pc_time, mw_times[i]))
                break
                
    # print time_matches
    return TimeBase(time_matches, pc_file_offset)
    

    
if __name__ == "__main__":
    
    import sys
    import matplotlib.pylab as plt
    project_path = sys.argv[1]
    cache_dir = "/tmp/phys"

    logging.info("Reading in data...")
    (pc_data, fs) = read_pixel_clock( project_path, 1 , cache_dir, 
                                      time_range=(0,1200))
    
    logging.info("Parsing data...")
    events, latencies = parse_pixel_clock( pc_data, 0.0, fs)
    
    print latencies
    
    do_plot = False
    
    if do_plot:
        logging.info("Plotting...")
        min_range = 0
        max_range = -1

        stride = 50
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
            plt.text(e.time, text_level, str(e.code))
    
        plt.show()
    
    #print(events)
