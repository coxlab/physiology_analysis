#!/usr/bin/env python

import logging, optparse, os, sys
logging.basicConfig(level = logging.DEBUG)

import numpy as np
import pylab as pl

import physio

# AP coordinates with P = -
sliceBounds = {   70: -4.36,
    71: -4.56,
    72: -4.68,
    73: -4.80,
    74: -4.92,
    75: -5.04,
    76: -5.20,
    77: -5.28,
    78: -5.40,
    79: -5.52,
    80: -5.64,
    81: -5.76,
    82: -5.88,
    83: -6.00,
    84: -6.12,
    85: -6.24,
    86: -6.36,
    87: -6.48,
    88: -6.60,
    89: -6.72,
    90: -6.84,
    91: -6.96,
    92: -7.08,
    93: -7.20,
    94: -7.32,
    95: -7.44,
    96: -7.56,
    97: -7.68,
    98: -7.80,
    99: -7.92,
    100: -8.04,
    101: -8.16,
    102: -8.28,
    103: -8.40,
    104: -8.52,
    105: -8.64,
    106: -8.76,
    107: -8.88}

parser = optparse.OptionParser(usage="usage: %prog [options] session")
parser.add_option("-o", "--outdir", dest="outdir", default="",
                    help="Output directory", type='str')

(options, args) = parser.parse_args()
if len(args) < 1:
    parser.print_usage()
    sys.exit(1)

config = physio.cfg.load(args[0])

epochs = []
if len(args) == 2:
    epochs = [int(args[1]),]
else:
    epochs = range(physio.session.get_n_epochs(config))


for epochNumber in epochs:
    session = physio.session.load(args[0], epochNumber)
    if True or options.outdir.strip() == '':
        #config = physio.cfg.load(args[0])
        outdir = physio.session.get_epoch_dir(config, epochNumber)
        # outdir = config.get('session','output')
        outdir += '/plots'
        options.outdir = outdir

    if not os.path.exists(options.outdir): os.makedirs(options.outdir)

    locations = session.get_channel_locations()
    logging.debug("Locations: %s" % str(locations))

    def skull_to_pixel(ml, dv, sliceIndex, imShape):
        if sliceIndex > 102:
            dv = dv + 1.
        #return x * self.imageSize[0]/16.0 + self.imageSize[0]/2., self.imageSize[1] + self.imageSize[1]/11.0 * y
        x = ml * imShape[1]/16.0 + imShape[1] / 2.
        y = dv * imShape[0]/11.0
        return x, y #x / 8., y / 5.5 + 1.

    for (ch, location) in zip(range(1,33), locations):
        # generate plot of position on atlas slice
        pl.clf()
        # ml - ap - dv
        ml, ap, dv = location
        sliceIndex = 0
        for (k, v) in sliceBounds.iteritems():
            if ap > v:
                sliceIndex = k
                break
        
        if sliceIndex == 0: physio.utils.error("Could not find slice index for: %f" % ap, ValueError)
        
        atlasDir = config.get('filesystem','atlas')
        sliceFile = '%s/%03i.png' % (atlasDir, k)
        
        im = pl.imread(sliceFile)
        
        pl.imshow(im)
        
        # convert ml, dv to pixel coordinates
        x, y = skull_to_pixel(ml, -dv, sliceIndex, im.shape)
        logging.debug("Channel: %i at %.3f %.3f %.3f" % (ch, ml, ap, dv))
        pl.scatter(x, y, color = 'r')
        pl.axhline(y, linestyle = '-.', color = 'b')
        pl.axvline(x, linestyle = '-.', color = 'b')
        pl.text(x-10, y+10, "%.3f, %.3f, %.3f" % (ml, ap, dv), ha = 'right', va = 'top')
        
        pl.title("Channel: %i" % ch)
        pl.xlabel("ML (mm)")
        pl.ylabel("DV (mm)")
        
        # reset axes
        pl.xlim(0,im.shape[1])
        pl.ylim(im.shape[0],0)
        pl.xticks(np.linspace(0,im.shape[1],17), range(-8,9,1))
        if sliceIndex > 102:
            pl.yticks(np.linspace(0,im.shape[0],12), range(1,13,1))
        else:
            pl.yticks(np.linspace(0,im.shape[0],12), range(0,12,1))
        
        pl.savefig('%s/atlas_%i.png' % (options.outdir, ch))


# config.get('filesystem','atlas')
# 
# imread()

# channels = range(1,33)
# clusters = range(1,6)
# 
# subplotsWidth = len(channels)
# subplotsHeight = len(clusters)
# pl.figure(figsize=(subplotsWidth*2, subplotsHeight*2))
# # pl.gcf().suptitle('%s %d' % (groupBy, group))
# pl.subplot(subplotsHeight, subplotsWidth,1)
# pl.subplots_adjust(left = 0.025, right = 0.975, top = 0.9, bottom = 0.1, wspace = 0.45)
# logging.debug("Plotting %i by %i plots(%i)" % (subplotsWidth, subplotsHeight, subplotsWidth * subplotsHeight))
# 
# for (y, cluster) in enumerate(clusters):
#     for (x, channel) in enumerate(channels):
#         logging.debug("\tPlotting[%i, %i]: ch %s : cl %s" % (x, y, channel, cluster))
#         spikes = session.get_spike_times(channel, cluster)
#         pl.subplot(subplotsHeight, subplotsWidth, subplotsWidth * y + x + 1)
#         physio.plotting.psth.plot(trialTimes, spikes, options.before, options.after, options.nbins)
#         #physio.plotting.raster.plot(trialTimes, spikes, options.before, options.after)
#         pl.axvline(0., color = 'k')
#         pl.axvspan(0., 0.5, color = 'k', alpha = 0.1)
#         
#         if x == 0:
#             pl.ylabel('Cluster: %i\nRate(Hz)' % cluster)
#         #else:
#         #    pl.yticks([])
#         if y == 0: pl.title('Ch:%i' % channel, rotation=45)
#         if y < len(clusters) - 1:
#             pl.xticks([])
#         else:
#             pl.xticks([0., .5])
#             pl.xlabel("Seconds")
# 
# session.close()
# 
# if not os.path.exists(options.outdir): os.makedirs(options.outdir) # TODO move this down
# pl.savefig("%s/bluesquare.png" % (options.outdir))
