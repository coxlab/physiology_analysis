#!/usr/bin/env python

import ast, logging, sys

import tables

import h5_utils
import pixel_clock
import stats

def load(h5filename, clean=True, addToBlacklist=['BlueSquare',]): # hack for addToBlacklist
    f = tables.openFile(h5filename)
    epoch_mw = h5_utils.get_mw_epoch(f)
    tb = pixel_clock.TimeBase(*h5_utils.get_time_matches(f))
    tb.audio_offset = -tb.mw_time_to_audio(epoch_mw[0])
    stimtimer = h5_utils.get_stimtimer(f, addToBlacklist)
    spiketimes = [ x["time"] for x in f.root.SpikeTable.iterrows()]
    clusters = [ x["clu"] for x in f.root.SpikeTable.iterrows()]
    triggers = [ x["st"] for x in f.root.SpikeTable.iterrows()]
    # waveforms = [ x["wave"] for x in f.root.SpikeTable.iterrows()]
    probe_dict = h5_utils.get_probe_gdata(f)
    bad_nn_channels = ast.literal_eval('['+probe_dict['badsites']+']')
    if bad_nn_channels == [None]:
        bad_nn_channels = []
    # if clean:
    #     spiketimes, clusters, triggers = stats.clean_spikes(spiketimes, clusters, triggers, bad_nn_channels)
    return f, tb, stimtimer, spiketimes, clusters, triggers, epoch_mw

def load_cluster(h5filename, clusterid, addToBlacklist=['BlueSquare',]):
    f = tables.openFile(h5filename)
    epoch_mw = h5_utils.get_mw_epoch(f)
    tb = pixel_clock.TimeBase(*h5_utils.get_time_matches(f))
    tb.audio_offset = -tb.mw_time_to_audio(epoch_mw[0])
    stimtimer = h5_utils.get_stimtimer(f, addToBlacklist)
    matchString = "clu == %i" % clusterid
    spiketimes = [ x["time"]/44100. for x in f.root.SpikeTable.where(matchString)]
    f.close()
    return tb, stimtimer, spiketimes, epoch_mw

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "usage: load.py <h5resultsfilename>"
    logging.basicConfig(level=logging.DEBUG)
    h5file, timebase, stimtimer, spiketimes, clusters, triggers, epoch = load(sys.argv[1])