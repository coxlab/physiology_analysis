#!/usr/bin/env python

import numpy as np
import pylab as pl

from .. import utils

def spc_temp(resultsFile, channel):
    with utils.H5Maker(resultsFile, 'r') as rf:
        nodeName = '/SPC/ch%i' % channel
        if not (nodeName in rf): utils.error("Node %s does not exist" % nodeName)
        
        spcNode = rf.getNode(nodeName)
        t = np.array(spcNode.ctree)
        
        pl.plot(t[:,3:])
        pl.xlabel('Temperature')
        pl.ylabel('Units per cluster')
        pl.title('Channel %i' % channel)
        
        nlines = t[:,3:].shape[1]
        labels = [str(i) for i in xrange(0,nlines)]
        
        pl.legend(labels)