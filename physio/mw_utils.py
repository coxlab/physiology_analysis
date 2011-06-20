import ast, os

import tables

global MWEnabled
try:
    import mworks.data as mw
    MWEnabled = True
except ImportError:
    MWEnabled = False

import matplotlib.pylab as plt

class MWReader(object):
    def __init__(self, filename):
        self.fn = filename
        self.f = mw.MWKFile(self.fn)
    def open(self):
        self.f.open()
    def get_events(self,codes=[]):
        return self.f.get_events(codes=codes)
    def get_codec(self):
        return self.f.codec
    def get_reverse_codec(self):
        return self.f.reverse_codec
    # --- common --
    def get_parsed_events(codes=[]):
        """
        Returns t [times], c [codes], and v [values] for events in codes
        """
        evs = self.get_events(cdoes)
        t = []
        c = []
        v = []
        for e in evs:
            t.append(e.time)
            c.append(e.code)
            v.append(e.value)
        return t, c, v
    def close(self):
        self.f.close()

class Event(object):
    def __init__(self, time, code, value):
        self.time = time
        self.code = code
        self.value = value

class H5Reader(MWReader):
    def __init__(self, filename):
        self.fn = filename
        self.t = None
    def open(self):
        self.t = tables.openFile(self.fn)
    def _get_value(self,atIndex):
        v = self.t.listNodes('/')[0].values[atIndex]
        try:
            return ast.literal_eval(v)
        except:
            return v
    def get_events(self,codes=[]):
        """
        This is terribly inefficient at the moment
        """
        rcodec = self.get_reverse_codec()
        cs = [rcodec[c] for c in codes]
        eventTable = self.t.listNodes('/')[0].events
        events = []
        for code, valueIndex, time in eventTable.cols:
            if code in cs:
                events.append(Event(time, code, self._get_value(valueIndex)))
        return events
    def get_codec(self):
        codec = self.t.listNodes('/')[0].codec
        r = {}
        for c in codec.cols:
            r[c[0]] = c[1]
        return r
    def get_reverse_codec(self):
        codec = self.get_codec()
        r = {}
        for k in codec:
            r[codec[k]] = k
        return r
    def close(self):
        if not (self.t is None):
            self.t.close()

def make_reader(filename):
    global MWEnabled
    if not MWEnabled:
        return H5Reader(filename)
    # check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.mwk':
        return MWReader(filename)
    else:
        return H5Reader(filename)

def extract_events(mw_filename, event_name, **kwargs):
    
    offset = kwargs.get("time_offset", 0.0)
    
    f = make_reader(mw_filename)
    # f = mw.MWKFile(mw_filename)
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

def event_lock_spikes( event_times, spike_times, pre_time, post_time, time_base=None, mw_offset=0 ):
    
    event_locked = []
    
    
    for e in event_times:
        # convert mworks time to audio time if time_base is defined
        if not (time_base is None): e = time_base.mw_time_to_audio(e, mw_offset)
        # this is inefficient for now
        relevant_spikes = filter( lambda x: x > e-pre_time and \
                                            x < e+post_time, spike_times)
        event_spikes = [ sp - e for sp in relevant_spikes ]
        event_locked.append(event_spikes)
    
    return event_locked
    
def plot_rasters(event_locked, **kwargs):
    
    v_spacing = kwargs.get("vertical_spacing", 0.05)
    time_range = kwargs.get("time_range", (-0.100, 0.500))
    
    n_events = len(event_locked)
    print("Plotting %d events" % (n_events))
    
    #plt.figure()
    plt.hold(True)
    plt.axvline(0.0, alpha=0.5)
    
    ts = []
    for i in range(0, n_events):
        y = (n_events - i)
        evt = event_locked[i]
        
        for t in evt:
            plt.plot( t, y, '|k')
            ts.append(t)
    
    if len(ts) != 0:
        plt.hist(ts,bins=plt.linspace(time_range[0],time_range[1],25),alpha=0.5,color='k') # bin into 24 bins
    
    plt.xlim(time_range)
    #plt.show()
        