#!/usr/bin/env python

import subprocess

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
    
    if not os.path.exists(audioDir): os.makedirs(audioDir)
    if not os.path.exists(resultsDir): os.makedirs(resultsDir)
    assert iterable(timerange), "timerange[%s] must be iterable" % str(timerange)
    assert len(timerange) == 2, "timerange length[%i] must be 2" % len(timerange)
    
    cmd = "parallel -j %i -t %i:%i -pv {} %s/{/.} ::: %s/input_*" %\
            (njobs, int(timerange[0]), int(timerange[1]), resultsDir, audioDir)
    p = subprocess.popen(cmd.split(), stderr = subprocess.PIPE, stdout = subprocess.PIPE)
    stdout, stderr = p.communicate()
    return stdout, stderr

def test_cluster():
    # TODO : how do I deal with external data?
    pass

if __name__ == '__main__':
    test_cluster()