import logging, os, pickle

import numpy as np
import tables

def group_to_dictionary(group, keyArray='keys', valArray='values'):
    """
    Construct a dictionry from a h5 group that contains two arrays (keyArray, valArray)
    """
    keys = group.keys.read()
    values = group.values.read()
    if len(keys) != len(values):
        raise AttributeError('NRows of keys[%d] != values[%d]' % (len(keys), len(values)))
    d = {}
    for k, v in zip(keys, values):
        d[k] = v
    return d

# TODO make utility for writing that uses with to make sure things get cleaned up and
#  to handle string or tables.file objects as first argument to write functions

def write_array(filename, data, name, title):
    """
    TODO document
    """
    logging.debug("Writing array %s to hdf5 file %s" % (name, filename))
    f = tables.openFile(filename, 'a')
    if '/%s' % name in f:
        logging.debug("Removing existing /%s from %s" % (name, filename))
        f.removeNode('/%s' % name, recursive = True)
    f.createArray('/',name, data, title = title)
    f.flush()
    f.close()

def write_dict(filename, data, name, title):
    logging.debug("Writing dictionary %s to hdf5 file %s" % (name, filename))
    f = tables.openFile(filename, 'a')
    if '/%s' % name in f:
        logging.debug("Removing existing /%s from %s" % (name, filename))
        f.removeNode('/%s' % name, recursive = True)
    g = f.createGroup('/', name, title)
    keys = f.createVLArray(g, 'keys', tables.VLStringAtom(), "keys", expectedsizeinMB=0.0001)
    values = f.createVLArray(g, 'values', tables.VLStringAtom(), "values", expectedsizeinMB=0.0001)
    for (k,v) in data.iteritems():
        keys.append(k)
        values.append(str(v))
    f.flush()
    f.close()

def write_epoch_audio(filename, epoch_audio):
    logging.debug("Writing epoch_audio[%s] to hdf5 file %s" % (str(epoch_audio), filename))
    f = tables.openFile(filename, 'a')
    f.root._v_attrs.EPOCH_START_AUDIO = epoch_audio[0]
    f.root._v_attrs.EPOCH_END_AUDIO = epoch_audio[1]
    f.flush()
    f.close()

def write_git_commit_id(filename, commitId):
    logging.debug("Writing git commit id[%s] to hdf5 file %s" % (str(commitId), filename))
    f = tables.openFile(filename, 'a')
    f.root._v_attrs.GIT_COMMIT_ID = commitId
    f.flush()
    f.close()

# ----------------- Old -------------------

import mw_utils
import stimsorter

class H5ResultsFileSaver(object):
    def __init__(self, spikesFilename):
        # /<TABLE:DatChannels/SpikeTable>
        self.spikeFile = tables.openFile(spikesFilename, mode='a')
    
    def add_session_h5_file(self, sessionFilename):
        #/<GROUP:session: K4_110715>/<TABLE:codec/events/values>
        # check that sessionFilename ends in .h5
        if os.path.splitext(sessionFilename)[1].lower() != '.h5':
            # if not, do special conversion to h5 (see mw_utils?) or throw error
            logging.error('attempted to merge non .h5 session file: %s' % sessionFilename)
            raise IOError('attempted to merge non .h5 session file: %s' % sessionFilename)
        
        # check if session info already exists in h5 file, if so, remove it
        sessionName = os.path.splitext(os.path.basename(sessionFilename))[0]
        nodeName = '/%s' % sessionName
        if nodeName in self.spikeFile:
            logging.info("Removing existing %s from spikeFile" % nodeName)
            self.spikeFile.removeNode(nodeName,recursive=True)
        
        # open mwk file and merge with spikeFile
        mf = tables.openFile(sessionFilename)
        logging.info("Merging %s with results file" % sessionFilename)
        mf.copyChildren(mf.root, self.spikeFile.root, recursive=True)
        self.spikeFile.flush()
        mf.close()
    
    def add_mw_epoch_times(self, start_mw, end_mw):
        """
        Save start and end times (in mw units) in h5 results file.
        These times should agree with the audio clipping range and account for
        any settling time used during the analysis.
        """
        self.spikeFile.root.SpikeTable.attrs.STARTMW = start_mw
        self.spikeFile.root.SpikeTable.attrs.ENDMW = end_mw
        self.spikeFile.flush()
    
    def add_timebase(self, timebaseFilename):
        f = open(timebaseFilename,'rb')
        evt_zipper, audio_offset = pickle.load(f)
        f.close()
        if '/TimeMatches' in self.spikeFile:
            logging.info("Removing existing /TimeMatches from spikeFile")
            self.spikeFile.removeNode('/TimeMatches',recursive=True)
        logging.debug("Saving TimeMatches to spikeFile")
        self.spikeFile.createArray('/','TimeMatches',np.array(evt_zipper),title='PC - MW Time Matches')
        self.spikeFile.root.TimeMatches.attrs.AUDIOOFFSET = audio_offset
        self.spikeFile.flush()
    
    def add_session_gdata(self, sessionGData):
        if sessionGData is None:
            logging.warning("Attempting to write none-type session data to results file")
            return
        if '/SessionGData' in self.spikeFile:
            logging.info("Removing existing /SessionGData from spikeFile")
            self.spikeFile.removeNode('/SessionGData',recursive=True)
        group = self.spikeFile.createGroup('/', 'SessionGData', 'Session data from GDocs')
        keys = self.spikeFile.createVLArray(group, 'keys', tables.VLStringAtom(), "keys", expectedsizeinMB=0.0001)
        values = self.spikeFile.createVLArray(group, 'values', tables.VLStringAtom(), "values", expectedsizeinMB=0.0001)
        for (k,v) in sessionGData.iteritems():
            keys.append(k)
            values.append(str(v))
        self.spikeFile.flush()
    
    def add_probe_gdata(self, probeGData):
        if probeGData is None:
            logging.warning("Attempting to write none-type probe data to results file")
            return
        if '/ProbeGData' in self.spikeFile:
            logging.info("Removing existing /ProbeGData from spikeFile")
            self.spikeFile.removeNode('/ProbeGData',recursive=True)
        group = self.spikeFile.createGroup('/', 'ProbeGData', 'Session data from GDocs')
        keys = self.spikeFile.createVLArray(group, 'keys', tables.VLStringAtom(), "keys", expectedsizeinMB=0.0001)
        values = self.spikeFile.createVLArray(group, 'values', tables.VLStringAtom(), "values", expectedsizeinMB=0.0001)
        for (k,v) in probeGData.iteritems():
            keys.append(k)
            values.append(str(v))
        self.spikeFile.flush()
    
    def add_pad_positions(self, padPositions):
        # ML - AP - DV  [deepest(tip) -> shallowest]
        kkToPadPos=[2, 8, 6, 12, 4, 16, 0, 20, 13, 1, 7, 5, 17, 3, 11, 9, 22, 14, 30, 26, 18, 10, 28, 24, 29, 25, 19, 15, 31, 27, 23, 21]
        logging.debug("Reordering pads")
        orderedPositions = np.array([padPositions[k] for k in kkToPadPos])
        if '/PadPositions' in self.spikeFile:
            logging.info("Removing existing /PadPositions from spikeFile")
            self.spikeFile.removeNode('/PadPositions',recursive=True)
        logging.debug("Saving PadPositions to spikeFile")
        self.spikeFile.createArray('/','PadPositions',orderedPositions,title='ML-AP-DV')
        self.spikeFile.flush()
    
    def add_git_commit_id(self, gitCommitID):
        self.spikeFile.root.SpikeTable.attrs.GITCOMMITID = gitCommitID
        self.spikeFile.flush()
    
    def close(self):
        self.spikeFile.close()

def group_to_dictionary(group, keyArray='keys', valArray='values'):
    """
    Construct a dictionry from a h5 group that contains two arrays (keyArray, valArray)
    """
    keys = group.keys.read()
    values = group.values.read()
    if len(keys) != len(values):
        raise AttributeError('NRows of keys[%d] != values[%d]' % (len(keys), len(values)))
    d = {}
    for k, v in zip(keys, values):
        d[k] = v
    return d

# ================ Getting functions ==================

def get_time_matches(h5file):
    evt_zipper = np.array(h5file.getNode('/TimeMatches'))
    audio_offset = h5file.getNode('/TimeMatches').attrs.AUDIOOFFSET
    return evt_zipper, audio_offset

def get_mw_epoch(h5file):
    return h5file.root.SpikeTable.attrs.STARTMW, h5file.root.SpikeTable.attrs.ENDMW

def get_mw_event_reader(h5file):
    logging.debug("Getting mw event reader from %s" % str(h5file))
    reader = mw_utils.H5Reader("")
    reader.h5file = h5file
    reader.find_session_node()
    return reader

def get_session_gdata(h5file):
    return group_to_dictionary(h5file.getNode('/SessionGData'))

def get_probe_gdata(h5file):
    return group_to_dictionary(h5file.getNode('/ProbeGData'))

def get_pad_positions(h5file):
    return np.array(h5file.getNode('/PadPositions'))

def get_git_commit_id(h5file):
    return h5file.root.SpikeTable.attrs.GITCOMMITID

def get_stimtimer(h5file, addToBlacklist=['BlueSquare',], mwkf=None):
    stimtimer = stimsorter.StimTimer()
    stimtimer.blacklist += addToBlacklist
    if mwkf is None:
        mwkf = get_mw_event_reader(h5file)
    [stimtimer.process_mw_event(e) for e in mwkf.get_events(codes=['#announceStimulus',], time_range=get_mw_epoch(h5file))]
    
    return stimtimer