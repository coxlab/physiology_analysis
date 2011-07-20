import logging, os, pickle

import numpy as np
import tables

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
        
        # open mwk file and merge with spikeFile
        mf = table.openFile(sessionFilename)
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
        self.spikeFile.root.SpikeTable.STARTMW = start_mw
        self.spikeFile.root.SpikeTable.ENDMW = end_mw
        self.spikeFile.flush()
    
    def add_timebase(self, timebaseFilename):
        f = open(timebaseFilename,'rb')
        evt_zipper, audio_offset = pickle.load(f)
        f.close()
        if '/TimeMatches' in self.spikeFile:
            logging.info("Removing existing /TimeMatches from spikeFile")
            self.spikeFile.removeNode('/TimeMatches',recursive=True)
        logging.debug("Saving TimeMatches to spikeFile")
        self.spikeFile.createArray('/','TimeMatches',orderedPositions,title='PC - MW Time Matches')
        self.spikeFile.root.TimeMatches.attrs.AUDIOOFFSET = audio_offset
        self.spikeFile.flush()
    
    def add_session_gdata(self, sessionGData):
        if sessionGData is None:
            logging.warning("Attempting to write none-type session data to results file")
            return
        if '/SessionGData' in self.spikeFile:
            logging.info("Removing existing /SessionGData from spikeFile")
            self.spikeFile.removeNode('/SessionGData',recursive=True)
        group = self.spikeTable.createGroup('/', 'SessionGData', 'Session data from GDocs')
        keys = self.spikeTable.createVLArray(group, 'keys', tables.VLStringAtom(), "keys", expectedsizeinMB=0.0001)
        values = self.spikeTable.createVLArray(group, 'keys', tables.VLStringAtom(), "keys", expectedsizeinMB=0.0001)
        for (k,v) in sessionGData.iteritems():
            keys.append(k)
            values.append(v)
        self.spikeTable.flush()
    
    def add_probe_gdata(self, probeGData):
        if probeGData is None:
            logging.warning("Attempting to write none-type probe data to results file")
            return
        if '/ProbeGData' in self.spikeFile:
            logging.info("Removing existing /ProbeGData from spikeFile")
            self.spikeFile.removeNode('/ProbeGData',recursive=True)
        group = self.spikeTable.createGroup('/', 'ProbeGData', 'Session data from GDocs')
        keys = self.spikeTable.createVLArray(group, 'keys', tables.VLStringAtom(), "keys", expectedsizeinMB=0.0001)
        values = self.spikeTable.createVLArray(group, 'keys', tables.VLStringAtom(), "keys", expectedsizeinMB=0.0001)
        for (k,v) in probeGData.iteritems():
            keys.append(k)
            values.append(v)
        self.spikeTable.flush()
    
    def add_pad_positions(self, padPositions):
        # ML - AP - DV  [deepest(tip) -> shallowest]
        kkToPadPos=[2, 8, 6, 12, 4, 16, 0, 20, 13, 1, 7, 5, 17, 3, 11, 9, 22, 14, 30, 26, 18, 10, 28, 24, 29, 25, 19, 15, 31, 27, 23, 21]
        logging.debug("Reordering pads")
        orderedPositions = np.array([padPositions[k] for k in kkToPadPos])
        if '/PadLocations' in self.spikeFile:
            logging.info("Removing existing /PadLocations from spikeFile")
            self.spikeFile.removeNode('/PadLocations',recursive=True)
        logging.debug("Saving PadLocations to spikeFile")
        self.spikeFile.createArray('/','PadLocations',orderedPositions,title='ML-AP-DV')
        self.spikeFile.flush()
    
    def add_git_commit_id(self, gitCommitID):
        self.spikeFile.root.SpikeTable.attrs.GITCOMMITID = gitCommitID
        self.spikeFile.flush()
    
    def close(self):
        self.spikeFile.close()
