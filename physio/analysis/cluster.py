#!/usr/bin/env python

import glob, logging, os, subprocess

import numpy as np

from .. import utils

def cluster(audioDir, resultsDir, timeRange, options = '', njobs = 8, async = False):
    """
    Cluster all audio files for a given session
    
    Parameters
    ----------
    audioDir : string
        Path of directory that contains the session audio files
    resultsDir : string
        Path of directory to use for results
    timeRange : tuple
        Time range (in samples) over which to cluster
    options : string
        Additionall command line options to pass to pyc.py
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
    parallel -j njobs pyc.py <options> -t timeRange[0]:timeRange[1] -pv {} resultsDir/{/.} ::: audioDir/input_*
    """
    if not os.path.exists(resultsDir): os.makedirs(resultsDir)
    assert np.iterable(timeRange), "timeRange[%s] must be iterable" % str(timeRange)
    assert len(timeRange) == 2, "timeRange length[%i] must be 2" % len(timeRange)
    
    # cmd = "parallel -j %i pyc.py %s -t %i:%i -pv {} %s/{/.} :::" %\
    #             (njobs, options, int(timeRange[0]), int(timeRange[1]), resultsDir)
    
    cmd = "parallel -j %i pycluster.py {} timerange %i:%i outputdir %s/{/.} %s :::" %\
            (njobs, int(timeRange[0]), int(timeRange[1]), resultsDir, options)
    
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
    options = config.get('clustering','options')
    timeRange = [int(e * sf) for e in epoch_audio]
    logging.debug("timeRange %s" % str(timeRange))
    return cluster(audioDir, resultsDir, timeRange, options = options, njobs = 8, async = False)

if __name__ == '__main__':
    test_cluster()
