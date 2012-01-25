#!/usr/bin/env python

import argparse
import logging
import os

import numpy
#import pylab
from mayavi import mlab

import physio
import pywaveclus


nfeatures = 6


logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser(description=\
        "Plot the clustering results for a single channel")
parser.add_argument("session", action="store")
parser.add_argument("channel", action="store", type=int,\
        choices=range(1,33))
parser.add_argument("-o","--output", action="store",\
        default="")

args = parser.parse_args()

session_filename = args.session
channel = args.channel

if not (os.path.exists(session_filename)):
    raise IOError("Session file: %s does not exist" %\
            session_filename)

logging.debug("Opening %s" % session_filename)
session = physio.session.Session(session_filename)

n_clusters = session.get_n_clusters(channel)
logging.debug("Channel %i has %i clusters" % (channel, n_clusters))

spike_times = []
spike_waveforms = []
clusters = []
for cluster in xrange(n_clusters):
    st = session.get_spike_times(channel, cluster)
    sw = session.get_spike_waveforms(channel, cluster)
    if len(st) != len(sw):
        raise IOError("len(times)[%i] != len(waves)[%i]" % \
                (len(st), len(sw)))
    spike_times += list(st)
    spike_waveforms += list(sw)
    clusters += [cluster] * len(st)
    #if len(spike_times) > 10: break # skip out early for testing

logging.debug("Found %i spikes" % len(spike_times))
session.close()

logging.debug("Running PCA on waveforms")
features = pywaveclus.dsp.pca.features(spike_waveforms,nfeatures)
logging.debug("Features: %s" % str(features.shape))
# features.shape = (nwaves, nfeatures)

spike_times = numpy.array(spike_times)
spike_waveforms = numpy.array(spike_waveforms)
clusters = numpy.array(clusters)

if args.output != "":
    logging.debug("Saving data to output: %s" % args.output)
    data = numpy.vstack((spike_times,clusters,\
            features.T,spike_waveforms.T)).T
    output = args.output
    if os.path.isdir(output): # if dir, make filename
        output = '%s/%s_%i.npy' %\
                (output, session_filename, channel)
    elif os.path.splitext(output)[1] != '.npy': # if not check ext
        output += '.npy'
    numpy.save(output, data)


figure = mlab.figure(fgcolor=(1,1,1), size=(800,600))
figure.scene.disable_render = True
glyphs = mlab.points3d(features[:,0], features[:,1],\
        features[:,2], clusters, scale_mode='none',\
        mode='2dvertex', colormap='Paired')
mlab.scalarbar(glyphs, nb_labels = len(numpy.unique(clusters)),\
        orientation = 'vertical', label_fmt="%.0f")

figure.scene.disable_render = False
mlab.show()

#pylab.figure()
#colors = pylab.cm.jet(clusters/float(n_clusters-1))
#for x in xrange(nfeatures):
#    for y in xrange(nfeatures):
#        if y >= x: continue
#        pylab.subplot(nfeatures, nfeatures, x + (y*nfeatures) + 1)
#        fx = features[:,x]
#        fy = features[:,y]
#        pylab.scatter(fx, fy, c=colors)
#pylab.show()
