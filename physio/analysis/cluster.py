#!/usr/bin/env python

import glob, logging, os, re, shlex, subprocess

import numpy as np

from .. import channelmapping
from .. import h5
from .. import utils

def get_adjacent(inputFiles, n = 2):
    """
    n : number of neighbors on either side
    so n 1 = up to 2 files
       n 2 = up to 4 files
    """
    adjFiles = []
    depthToFile = {}
    depths = []
    for inputFile in inputFiles:
        # get channel number
        tdtch = h5.combine.find_channel(inputFile, r'[a-z,A-Z]+_([0-9]+)\#*')
        depth = channelmapping.tdt_to_position(tdtch)
        depthToFile[depth] = inputFile
        depths.append(depth)
    for d in depths:
        left = max(0,d-n)
        right = min(d+n,max(depths))
        files = []
        for i in xrange(left, right+1):
            if i != d: # don't include the center file
                files.append(depthToFile[i])
        adjFiles.append(files)
    return adjFiles


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
    
    cmd = """parallel --xapply -j %i pycluster.py {1} timerange %i:%i outputdir %s/{1/.} %s :::""" %\
            (njobs, int(timeRange[0]), int(timeRange[1]), resultsDir, options)
    
    inputFiles = glob.glob(audioDir+'/input_*')
    for inputFile in inputFiles:
        cmd += " " + os.path.basename(inputFile) + " "
    
    #adjFiles = get_adjacent(inputFiles)
    #cmd += " ::: "
    #for adjFile in adjFiles:
    #    cmd += "'" + '"'
    #    for adj in adjFile:
    #        cmd += os.path.basename(adj) + " "
    #    cmd = cmd[:-1] + '"' + "' " # removes last space

    logging.debug("Running: %s" % cmd)
    splitcmd = shlex.split(cmd)
    logging.debug("Running: %s" % str(splitcmd))
    p = subprocess.Popen(splitcmd, stderr = subprocess.PIPE, stdout = subprocess.PIPE, cwd = audioDir)
    if async:
        return p
    else:
        stdout, stderr = p.communicate()
        logging.debug("Return code: %i" % p.returncode)
        if p.returncode != 0: utils.error("Clustering failed:\n\tstdout:%s\n--\nstderr:%s" % (stdout, stderr))
        return stdout, stderr

def cluster_with_adjacent(audioDir, resultsDir, timeRange, options = '', njobs = 8, async = False, nadjacent = 2):
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
    
    cmd = """parallel --xapply -j %i pycluster.py {1} timerange %i:%i outputdir %s/{1/.} adjacentfiles '{2}' %s :::""" %\
            (njobs, int(timeRange[0]), int(timeRange[1]), resultsDir, options)
    
    inputFiles = glob.glob(audioDir+'/input_*')
    for inputFile in inputFiles:
        cmd += " " + os.path.basename(inputFile) + " "
    
    adjFiles = get_adjacent(inputFiles, nadjacent)
    cmd += " ::: "
    for adjFile in adjFiles:
        cmd += "'" + '"'
        for adj in adjFile:
            cmd += os.path.basename(adj) + " "
        cmd = cmd[:-1] + '"' + "' " # removes last space

    logging.debug("Running: %s" % cmd)
    splitcmd = shlex.split(cmd)
    logging.debug("Running: %s" % str(splitcmd))
    p = subprocess.Popen(splitcmd, stderr = subprocess.PIPE, stdout = subprocess.PIPE, cwd = audioDir)
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
    njobs = config.getint('clustering','njobs')
    nadj = config.getint('clustering','nadjacent')
    if nadj == 0:
        return cluster(audioDir, resultsDir, timeRange, options = options, njobs = njobs, async = False)
    else:
        return cluster_with_adjacent(audioDir, resultsDir, timeRange, options = options, njobs = njobs, async = False, nadjacent = nadj)

if __name__ == '__main__':
    test_cluster()
