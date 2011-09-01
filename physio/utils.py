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