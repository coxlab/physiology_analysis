#!/usr/bin/env python

import logging, optparse, os, sys
logging.basicConfig(level = logging.DEBUG)
#import matplotlib
import numpy as np
import pylab as pl

import physio

parser = optparse.OptionParser(usage="usage: %prog [options] session epochNumber channel cluster")
parser.add_option("-b", "--baselineStart", dest="baselineStart", default=-0.1,
                    help="Seconds (relative to stimulus) to start baseline calculation window", type='float')
parser.add_option("-B", "--baselineEnd", dest="baselineEnd", default=0.,
                    help="Seconds (relative to stimulus) to end baseline calculation window", type="float")
parser.add_option("-r", "--responseStart", dest="responseStart", default=0.05,
                    help="Seconds (relative to stimulus) to start response calculation window", type='float')
parser.add_option("-R", "--responseEnd", dest="responseEnd", default=0.15,
                    help="Seconds (relative to stimulus) to end response calculation window", type="float")
parser.add_option("-o", "--outdir", dest="outdir", default="",
                    help="Output directory", type="str")

parser.add_option("--fixed_pos_x", dest="fixed_pos_x", default=None,
                    help="Hardcoded x pos", type="float")
parser.add_option("--fixed_pos_y", dest="fixed_pos_y", default=None,
                    help="Hardcoded y pos", type="float")

parser.add_option("-f", "--filter_gaze", dest="gaze_filter", action="store_true",
                    help="Filter by gaze fidelity", default=False)

parser.add_option("-n", "--normalized", dest="normalized", action="store_true",
                    help="Normalize by peak firing rate", default=False)

(options, args) = parser.parse_args()
if len(args) != 4:
    parser.print_usage()
    sys.exit(1)

(sessionName, epochNumber, channel, cluster) = args
epochNumber = int(epochNumber)
channel = int(channel)
cluster = int(cluster)

rwin = (options.responseStart, options.responseEnd)  # (0.05,0.15)
bwin = (options.baselineStart, options.baselineEnd)  # (-0.1,0)

#sessionName = 'L2_110927'
#epochNumber = 0
#channel = 6
#cluster = 2

config = physio.cfg.load(sessionName)
#epochs = []
#if len(args) == 2:
#    epochs = [int(args[1]),]
#else
#    epochs = range(physio.session.get_n_epochs(config))

session = physio.session.load(sessionName, epochNumber)

spikes = session.get_spike_times(channel, cluster)

# get baseline firing rate

if options.gaze_filter:
    logging.debug("Loading gaze filtered trials")
    trialTimes, stimuli, _, _ = session.get_gaze_filtered_trials()
else:
    trialTimes, stimuli, _, _ = session.get_trials()

targetTimes, blueStimuli = session.get_stimuli(stimType='rectangle')
allStimTimes = trialTimes + targetTimes
assert len(trialTimes) + len(targetTimes) == len(allStimTimes)

# get driven firing rate
bspikes = physio.spikes.stats.event_lock(allStimTimes, spikes, bwin[0], bwin[1], unpack=True)
brate = len(bspikes) / (float(bwin[1] - bwin[0]) * len(allStimTimes))
print "Baseline rate: %f spikes per second" % brate

# get all stim ids, stim positions, stim sizes
uniqueStimuli = physio.events.stimuli.unique(stimuli)
ids = {}
sizes = {}
posxs = {}
posys = {}
for s in uniqueStimuli:
    ids[s['name']] = 1
    sizes[s['size_x']] = 1
    posxs[s['pos_x']] = 1
    posys[s['pos_y']] = 1
ids = sorted(ids.keys())
sizes = sorted(sizes.keys())
posxs = sorted(posxs.keys())
posys = sorted(posys.keys())
print ids, sizes, posxs, posys

# sort id by response (plot id)
idRates = {}
idRateSEs = {}
for stimId in ids:
    trials, _, _, _ = session.get_trials({'name': stimId})
    sspikes = physio.spikes.stats.event_lock(trials, spikes, rwin[0], rwin[1])
    #print sspikes.shape, trials.shape
    tspikes = [len(s) for s in sspikes]
    #idRates[stimId] = len(sspikes) / (float(rwin[1] - rwin[0]) * len(trials))
    idRates[stimId] = pl.mean(tspikes) / (float(rwin[1] - rwin[0]))
    idRateSEs[stimId] = pl.std(tspikes) / (float(rwin[1] - rwin[0]) * pl.sqrt(len(tspikes)))
    #idRateSEs[stimId] = pl.std(tspikes) / (float(rwin[1] - rwin[0]))

print "ID Rates:", idRates
idByRate = sorted(idRates, key=idRates.get)
minId = idByRate[0]
maxId = idByRate[-1]
midI = int(len(idByRate)/2)
midId = idByRate[midI]
print "Min, mid, max:", minId, midId, maxId


pl.figure(figsize=(18, 6))

pl.suptitle("%s:%i[%i]" % (sessionName, channel, cluster))
pl.subplot(1, 4, 1)
rates = [idRates[i] for i in idByRate]
ses = [idRateSEs[i] for i in idByRate]
names = idByRate
colors = ['k' for i in xrange(len(rates))]
colors[0] = 'b'
colors[midI] = 'g'
colors[-1] = 'r'
pl.bar(range(len(rates)), rates, yerr=ses, color=colors, ecolor='k')
#pl.vlines(range(len(rates)), pl.zeros(len(rates)), rates, colors=colors, lw=5.0)
pl.xticks(pl.arange(len(rates)) + 0.4, names)
pl.ylabel("Firing Rate (Hz)")
pl.axhline(brate)
pl.xlabel("Stimulus Id")
pl.xlim((-1, len(rates) + 1))


def get_rate(spikes, condition, rwin):
    trials, _, _, _ = session.get_trials(condition)
    if len(trials) == 0:
        raise ValueError("no trials for condition: %s" % str(condition))
    s = [len(ts) for ts in physio.spikes.stats.event_lock(trials, spikes, rwin[0], rwin[1])]
    ms = pl.mean(s) / (float(rwin[1] - rwin[0]))
    ss = pl.std(s) / (float(rwin[1] - rwin[0]) * pl.sqrt(len(s)))
    nt = len(s)
    return ms, ss, nt


# collapse across size (plot position)
poss = []
for y in posys:
    row = []
    for x in posxs:
        row.append(x)
    poss.append(row)

rateByPos = pl.ones((3, len(posys), len(posxs))) * brate
rateByPosSE = pl.ones((3, len(posys), len(posxs))) * brate
for (ii, i) in enumerate((minId, midId, maxId)):
    for (iy, y) in enumerate(posys):
        for (ix, x) in enumerate(posxs):
            try:
                m, s, n = get_rate(spikes, {'name': i, 'pos_x': x, 'pos_y': y}, rwin)
                rateByPos[ii, iy, ix] = m
                rateByPosSE[ii, iy, ix] = s
                # TOIDLSKDJFSODFIJSDO adding SE
                #rates.append(get_rate(spikes, {'name': i, 'pos_x': x, 'pos_y':y}, rwin))
            except ValueError as E:
                print E
                rateByPos[ii, iy, ix] = pl.nan
                rateByPosSE[ii, iy, ix] = pl.nan
print rateByPos
cmaps = (pl.cm.Blues, pl.cm.Greens, pl.cm.Reds)


max_response = max(rateByPos.ravel())

pl.subplot(1, 4, 2)
pl.title('Worst stim')
pl.imshow(rateByPos[0, :, :] / max_response)

pl.subplot(1, 4, 3)
pl.title('Middle stim')
pl.imshow(rateByPos[1, :, :] / max_response)

pl.subplot(1, 4, 4)
pl.title('Best stim')
pl.imshow(rateByPos[2, :, :] / max_response)

#pl.subplot(133)

# spw = len(posxs) * 3
# sph = len(posys)
# ymax = 0
# ax = None
# for iy in xrange(len(posys)):
#     for ix in xrange(len(posxs)):
#         # check if nan
#         rates = rateByPos[:, iy, ix]
#         ses = rateByPosSE[:, iy, ix]
#         if any(pl.isnan(rates)):
#             continue
#         if ax is None:
#             ax = pl.gcf().add_subplot(sph, spw, len(posxs) * 2 + ix + iy * spw + 1)
#         else:
#             pl.gcf().add_subplot(sph, spw, len(posxs) * 2 + ix + iy * spw + 1, sharex=ax, sharey=ax)

#         pl.bar(range(len(rates)), rates, yerr=ses, color=('b', 'g', 'r'), ecolor='k')
#         #if iy != (len(posys)-1): pl.xticks([])
#         #if ix != 0: pl.yticks([])
#         pl.axhline(brate)
#         ymax = max(ymax, pl.ylim()[1])

# for iy in xrange(len(posys)):
#     for ix in xrange(len(posxs)):
#         rates = rateByPos[:, iy, ix]
#         ses = rateByPosSE[:, iy, ix]
#         if any(pl.isnan(rates)):
#             continue


# save plot
extras = ''
if options.fixed_pos_x is not None:
    extras += '_pos_x_%d' % options.fixed_pos_x

if options.fixed_pos_y is not None:
    extras += '_pos_y_%d' % options.fixed_pos_y

if options.gaze_filter:
    extras += '_gf'

if options.normalized:
    extras += '_normed'

pl.savefig("maps_%s_ch%dcl%d%s.pdf" % (sessionName, channel, cluster, extras))
