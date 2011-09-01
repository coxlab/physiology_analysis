#!/usr/bin/env python

import glob, logging, os, re, sys, time
from contextlib import contextmanager

import numpy as np
import tables

class H5Maker:
    """
    Accepts either a file or string (filename) and allows with(file/filename) for h5 files
    """
    def __init__(self, file_or_filename, *args, **kwargs):
        """
        Parameters
        ----------
        file_or_filename : str or h5file
            Filename of h5 file or a pytables h5file object
        args, kwargs : variable arguments
        """
        if type(file_or_filename) is str:
            self._file = tables.openFile(file_or_filename, *args, **kwargs)
            self._wasFile = False
        else:
            self._file = file_or_filename
            self._wasFile = True
    
    def __enter__(self):
        return self._file
    
    def __exit__(self, exc_type, exc_value, traceback):
        if not self._wasFile:
            self._file.flush()
            self._file.close()
        return False # propagate exception

def error(string, exception = Exception):
    """
    Wrapper around logging.error that also raises an exception
    
    Parameters
    ----------
    string : str
        Error description string
    exception : Exception
        Type of exception to raise
    """
    logging.error(string)
    raise exception(string)

def regex_glob(directory, regex):
    """
    Find all files in directory that match regex
    
    Parameters
    ----------
    directory : string
        Directory to check with os.listdir
    regex : string
        Regular expression to check file names. May contain groups
    
    Returns
    -------
    files : list
        List of files (with prepended directory) matching regex
    groups : list
        Groups from regex matches for each file in files
    """
    files = os.listdir(directory)
    outFiles = []
    groups = []
    for f in files:
        m = re.match(regex, f)
        if m is None: continue
        outFiles.append('/'.join((directory,f)))
        gs = m.groups()
        if len(gs) == 1:
            groups.append(gs[0])
        elif len(gs) > 1:
            groups.append(gs)
    return outFiles, groups

def get_git_commit_id():
    path = os.path.abspath(sys.argv[0]) # path of script
    cmd = "git log -n 1 --pretty=format:%%H %s" % path
    p = os.popen(cmd)
    return p.read()

# ----------------------- Old --------------------

@contextmanager
def waiting_file_lock(lock_file, delay=1):
    while os.path.exists(lock_file):
        logging.info("Found lock file, waiting to recheck in %d..." % delay)
        time.sleep(delay)
    open(lock_file, 'w').write("1")
    try:
        yield
    finally:
        os.remove(lock_file)

def get_git_commit_id():
    path = os.path.abspath(sys.argv[0]) # path of script
    cmd = "git log -n 1 --pretty=format:%%H %s" % path
    return os.popen(cmd).read()

def get_sessions(results_directory):
    matchstring = "session_*_to_*_a32_batch"
    return glob.glob('/'.join((results_directory, matchstring)))

def read_mw_epochs(data_directory, time_base, time_unit):
    """
    Read in epochs and automatically convert them to mw times
    """
    if time_unit == 'audio':
        epochs_audio = read_raw_epochs(data_directory)
        logging.debug("Loaded audio epochs: %s" % str(epochs_audio))
        ufunc_audio_to_mw = np.frompyfunc(time_base.audio_time_to_mw, 1, 1)
        epochs_mw = ufunc_audio_to_mw(epochs_audio)
        logging.debug("Converted epochs to mw time: %s" % str(epochs_mw))
        return epochs_mw
    elif time_unit == 'mworks':
        epochs = read_raw_epochs(data_directory)
        logging.debug("Loaded mworks epochs: %s" % str(epochs))
        return epochs
    else:
        logging.error("epochs timeunit: %s not valid" % time_unit)

def read_raw_epochs(data_directory):
    """
    Read in epochs without any conversion
    """
    epochs = []
    epochFilename = '/'.join((data_directory,"epochs"))
    if not (os.path.exists(epochFilename)):
        logging.info("No epoch file found: %s" % epochFilename)
        return epochs # epochFilename did not exist, so return the blank list
    else:
        # try to load the custom epoch file
        epochs = np.loadtxt(epochFilename)
        if epochs.ndim == 1:
            epochs = epochs.reshape((1,2))
        if epochs.shape[1] != 2:
            raise IOError("Epoch file shape incorrect: %s" % epochFilename) # epoch file was not shaped correctly
        return epochs

# def read_epochs_audio(data_directory):
#     """
#     Read in manually defined epoch time-ranges [in audio time units]
#     """
#     epochs = []
#     epochFilename = '/'.join((data_directory,"epochs"))
#     if not (os.path.exists(epochFilename)):
#         logging.info("No epoch file found: %s" % epochFilename)
#         return epochs # epochFilename did not exist, so return the blank list
#     else:
#         # try to load the custom epoch file
#         epochs = np.loadtxt(epochFilename)
#         if epochs.ndim == 1:
#             epochs = epochs.reshape((1,2))
#         if epochs.shape[1] != 2:
#             raise IOError("Epoch file shape incorrect: %s" % epochFilename) # epoch file was not shaped correctly
#         return epochs
# 
# def read_epochs_mw(data_directory, time_base):
#     """
#     Read in manually defined epoch time-ranges [in mw time units]
#     
#     this requires a time_base object that can map audio times to mworks times
#     """
#     audio_epochs = read_epochs_audio(data_directory)
#     ufunc_audio_to_mw = np.frompyfunc(time_base.audio_time_to_mw, 1, 1)
#     return ufunc_audio_to_mw(audio_epochs)

def save_mw_epochs(data_directory, epochs, time_base, time_unit):
    """
    Save epochs to a file. epochs should be in mworks time.
    time_unit will determine the saved unit (either audio or mworks)
    """
    outFile = '/'.join((data_directory,'epochs'))
    if time_unit == 'audio':
        np.savetxt(outFile,np.frompyfunc(time_base.mw_time_to_audio, 1, 1)(epochs))
    elif time_unit == 'mworks':
        np.savetxt(outFile,epochs)
    else:
        logging.error("epochs timeunit: %s not valid" % time_unit)

def make_output_dirs(config):
    tmp = config.get('filesystem','tmp')
    if not (os.path.exists(tmp)): os.makedirs(tmp)
    
    output_dir = config.get('session','output')
    if not (os.path.exists(output_dir)): os.makedirs(output_dir)
    
    scratch_dir = config.get('session','scratch')
    if not (os.path.exists(scratch_dir)): os.makedirs(scratch_dir)
    
    pixel_clock_scratch = config.get('pixel clock','scratch')
    if not (os.path.exists(pixel_clock_scratch)): os.makedirs(pixel_clock_scratch)
