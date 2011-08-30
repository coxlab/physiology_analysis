import ast, copy, logging, os, re

import tables

# --------------------- OLD --------------------

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
    def get_events(self,codes=[], time_range=None):
        ecodes = copy.deepcopy(codes)
        if time_range is None:
            return self.f.get_events(codes=ecodes)
        else:
            time_range = (int(time_range[0] * 1000000), int(time_range[1] * 1000000))
            return self.f.get_events(codes=ecodes, time_range=time_range)
    def get_codec(self):
        return self.f.codec
    def get_reverse_codec(self):
        return self.f.reverse_codec
    # --- common --
    def get_parsed_events(self,codes=[], time_range=None):
        """
        Returns t [times], c [codes], and v [values] for events in codes
        """
        evs = self.get_events(codes, time_range)
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
        self.h5file = None
        self.sessionNode = None
    
    def open(self):
        self.h5file = tables.openFile(self.fn)
        self.sessionNode = None
        
        # try to set session node by filenmae
        sessionName = '/%s' % os.path.splitext(os.path.basename(self.fn))[0]
        if sessionName in self.h5file:
            self.sessionNode = self.h5file.getNode(sessionName)
        else:
            # if not search for session node
            self.find_session_node()
    
    def find_session_node(self, regex=r'^[A-Z]+[0-9]+_[0-9]*'):
        logging.debug("Searching for session node in: %s" % str(self.h5file))
        for nodeName in self.h5file.root._v_children.keys():
            if bool(re.match(regex, nodeName)):
                self.sessionNode = self.h5file.getNode('/%s' % nodeName)
                return
        raise ValueError('Could not find session node')
    
    def _get_value(self,atIndex):
        v = self.sessionNode.values[atIndex]
        try:
            return ast.literal_eval(v)
        except:
            return v
    
    def get_events(self,codes=[], time_range=None):
        """
        This is terribly inefficient at the moment
        time_range is in seconds
        """
        rcodec = self.get_reverse_codec()
        cs = [rcodec[c] for c in codes]
        matchString = ' | '.join(['code == %i' % c for c in cs])
        logging.debug("using matchString: %s" % matchString)
        eventTable = self.sessionNode.events
        if time_range is None:
            events = [Event(e['time'],e['code'],self._get_value(e['index'])) for e in eventTable.where(matchString)]
        else:
            # PyTables version 2.2.1 does not support selection on uint64 (the time type) so...
            time_range = (time_range[0]*1000000, time_range[1]*1000000)
            events = [Event(e['time'],e['code'],self._get_value(e['index'])) for e in eventTable.where(matchString) if \
                            e['time'] >= time_range[0] and e['time'] <=time_range[1]]
        # for code, valueIndex, time in eventTable.cols:
        #     if code in cs:
        #         events.append(Event(time, code, self._get_value(valueIndex)))
        return events
    def get_codec(self):
        codec = self.sessionNode.codec
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
        if not (self.h5file is None):
            self.h5file.close()

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

def faster_event_lock_spikes( event_times, spike_times, pre_time, post_time, time_base):
    locked_all = []
    
    spikeN = len(spike_times)
    spikeI = 0
    for e in event_times:
        m = time_base.mw_time_to_audio(e)
        locked_event = []
        spikeI = 0
        while spikeI < spikeN:
            d = spike_times[spikeI] - m
            if d > pre_time and d < post_time:
                locked_event.append(d)
            elif d > post_time:
                break
                # spikeI = spikeN
            spikeI += 1
        locked_all.append(locked_event)
    
    return locked_all

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

def plot_psth(event_locked, **kwargs):

    time_range = kwargs.get("time_range", (-0.100, 0.500))
    n_bins = kwargs.get("n_bins", 25)
    bin_color = kwargs.get("bin_color", '0.5')

    n_events = len(event_locked)
    #print("Plotting %d events" % (n_events))

    #plt.figure()
    plt.hold(True)
    plt.axvline(0.0, zorder=-500)#alpha=0.5)

    ts = []
    for i in range(0, n_events):
        y = (n_events - i)
        evt = event_locked[i]

        for t in evt:
            ts.append(t)

    if len(ts) != 0:
        plt.hist(ts,bins=plt.linspace(time_range[0],time_range[1],n_bins),color=bin_color,zorder=-500) # bin into 24 bins

    plt.xlim(time_range)
    #plt.show()

def plot_rasters(event_locked, **kwargs):
    
    v_spacing = kwargs.get("vertical_spacing", 0.05)
    time_range = kwargs.get("time_range", (-0.100, 0.500))
    n_bins = kwargs.get("n_bins", 25)
    bin_color = kwargs.get("bin_color", '0.5')
    
    n_events = len(event_locked)
    #print("Plotting %d events" % (n_events))
    
    #plt.figure()
    plt.hold(True)
    plt.axvline(0.0, zorder=-500)#alpha=0.5)
    
    ts = []
    for i in range(0, n_events):
        y = (n_events - i)
        evt = event_locked[i]
        
        for t in evt:
            plt.plot( t, y, '|k')
            ts.append(t)
    
    if len(ts) != 0:
        plt.hist(ts,bins=plt.linspace(time_range[0],time_range[1],n_bins),color=bin_color,zorder=-500) # bin into 24 bins
    
    plt.xlim(time_range)
    #plt.show()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    mwkFile = '../data/K4_110523/K4_110523.mwk'
    h5File = '../data/K4_110523/K4_110523.h5'
    
    h5 = make_reader(h5File)
    h5.open()
    mw = make_reader(mwkFile)
    mw.open()
    
    mwc = mw.get_codec()
    h5c = mw.get_codec()
    
    if mwc != h5c:
        logging.error("Codecs did NOT match")
    
    blacklist = ['#announceCurrentState', '#announceMessage']
    
    for code in mwc.values():
        if code in blacklist:
            logging.debug("Not checking blacklisted code: %s" % code)
            continue
        mwes = mw.get_parsed_events([code,])
        h5es = h5.get_parsed_events([code,])
        logging.info("Code: %s" % code)
        logging.info("  mw: %i" % len(mwes[0]))
        logging.info("  h5: %i" % len(h5es[0]))
        if len(mwes[0]) != len(h5es[0]):
            logging.error("N of mw(%i) and h5(%i) events did not match for code %s" % (len(mwes[0]),len(h5es[0]),code))
        for i in xrange(len(mwes[0])):
            mwe = (mwes[0][i], mwes[1][i], mwes[2][i])
            h5e = (h5es[0][i], h5es[1][i], h5es[2][i])
            if mwe != h5e:
                logging.error("mw event(%s) and h5 event(%s) do not match" % (str(mwe), str(h5e)))
        logging.debug("Code %s passed" % code)
