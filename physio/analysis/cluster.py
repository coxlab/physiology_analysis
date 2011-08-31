#!/usr/bin/env python

import glob, logging, os, subprocess

import numpy as np

from .. import utils

def cluster(audioDir, resultsDir, timerange, njobs = 8, async = False):
    """
    Cluster all audio files for a given session
    
    Parameters
    ----------
    audioDir : string
        Path of directory that contains the session audio files
    resultsDir : string
        Path of directory to use for results
    timerange : tuple
        Time range (in samples) over which to cluster
    njobs : int
        Number of simultaneous jobs to run
    async : bool
        Run clustering asynchronously, will return popen object
    
    Results
    -------
    stdout : string
        Standard output of clustering process
    stderr : string
        Standard error of clustering process
    
    --- OR --- if async == True
    
    process : popen object
        Popen object of clustering process
            Use .poll() to check (returns NoneType if not)
            Use .communicate() to wait till done and return (stdout, stderr)
            see subprocess module for more info
    
    Notes
    -----
    parallel -j njobs pyc.py -t timerange[0]:timerange[1] -pv {} resultsDir/{/.} ::: audioDir/input_*
    """
    if not os.path.exists(resultsDir): os.makedirs(resultsDir)
    assert np.iterable(timerange), "timerange[%s] must be iterable" % str(timerange)
    assert len(timerange) == 2, "timerange length[%i] must be 2" % len(timerange)
    
    cmd = "parallel -j %i pyc.py -t %i:%i -pv '{}' '%s/{/.}' :::" %\
            (njobs, int(timerange[0]), int(timerange[1]), resultsDir)
    
    inputFiles = glob.glob(audioDir+'/input_*')
    for inputFile in inputFiles:
        cmd += " " + os.path.basename(inputFile) + " "
    
    logging.debug("Running: %s" % cmd)
    p = subprocess.Popen(cmd.split(), stderr = subprocess.PIPE, stdout = subprocess.PIPE, cwd = audioDir)
    if async:
        return p
    else:
        stdout, stderr = p.communicate()
        logging.debug("Return code: %i" % p.returncode)
        if p.returncode != 0: utils.error("Clustering failed:\n\tstdout:%s\n--\nstderr:%s" % (stdout, stderr))
        return stdout, stderr

def test_cluster():
    # TODO : how do I deal with external data?
    pass

def cluster_from_config(config, epoch_audio):
    audioDir = config.get('session','dir') + '/Audio Files'
    resultsDir = config.get('session','output')
    sf = config.getint('audio','samprate')
    timerange = [int(e * sf) for e in epoch_audio]
    logging.debug("timerange %s" % str(timerange))
    return cluster(audioDir, resultsDir, timerange, njobs = 8, async = False)

if __name__ == '__main__':
    test_cluster()
