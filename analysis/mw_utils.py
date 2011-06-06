import mworks.data as mw
import matplotlib.pylab as plt

def extract_events(mw_filename, event_name, **kwargs):
    
    offset = kwargs.get("time_offset", 0.0)
    
    f = mw.MWKFile(mw_filename)
    f.open()
    
    events = f.get_events(codes=[event_name])
    
    times = [ e.time for e in events ]
    values = [ e.value for e in events ]
    
    # corrected_times = [ ((t - times[0]) / 1.0e6) - offset for t in times]
    corrected_times = [ (t / 1.0e6) - offset for t in times]
    
    f.close()
    
    return (corrected_times, values)

def extract_and_group_stimuli(mw_filename, **kwargs):
    
    (times, values) = extract_events(mw_filename, '#announceStimulus', **kwargs)
    
    stim_names = [ v['name'] for v in values ]
    
    grouped_stim_times = {}
    
    for i in range(0, len(stim_names)):
        
        name = stim_names[i]
        
        if name not in grouped_stim_times:
            grouped_stim_times[name] = [ times[i] ]
        else:
            grouped_stim_times[name].append(times[i])
    
    return grouped_stim_times

def aggregate_stimuli( grouped_stimuli ):
    ks = grouped_stimuli.keys()
    agglom = []
    for key in ks:
        if key is not "pixel clock" and \
           key is not "BlueSquare" and \
           key is not "background" and \
           key is not "BlankScreenGray":
            
            agglom += grouped_stimuli[key]
    
    return agglom

def event_lock_spikes( event_times, spike_times, pre_time, post_time ):
    
    event_locked = []
    
    
    for e in event_times:
        
        # this is inefficient for now
        relevant_spikes = filter( lambda x: x > e-pre_time and \
                                            x < e+post_time, spike_times)
        event_spikes = [ sp - e for sp in relevant_spikes ]
        event_locked.append(event_spikes)
    
    return event_locked
    
def plot_rasters(event_locked, **kwargs):
    
    v_spacing = kwargs.get("vertical_spacing", 0.05)
    time_range = kwargs.get("time_range", (-0.050, 0.500))
    
    n_events = len(event_locked)
    print("Plotting %d events" % (n_events))
    
    #plt.figure()
    plt.hold(True)
    
    for i in range(0, n_events):
        y = (n_events - i)
        evt = event_locked[i]
        
        for t in evt:
            plt.plot( t, y, '|k')
    
    #plt.show()
        