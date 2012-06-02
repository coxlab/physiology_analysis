#!/usr/bin/env python

import clustermerge
import physio


# my options are
# - parse a summay file into a bunch of cells and itterate over them
# - generate a seperate dictionary of cells,
# have the main loop call that to see if all the channel/clusters
# have been loaded
# - first one is much easier
class CellSummary(physio.summary.Summary):
    def __init__(self, fn, overrides):
        physio.summary.Summary.__init__(self, fn)
        self.make_cells(overrides)

    def make_cells(self, overrides):
        """
        cells are lists of (ch, cl) pairs
        """
        merges = clustermerge.parse_merges(\
                overrides[self.session]['mergeclusters'].text)
        cellids = ['%i.%i' % (ch, cl) for ch in \
                self.get_channel_indices() for cl in \
                self.get_cluster_indices(ch)]
        self.cells = clustermerge.merge(cellids, merges)

    def cells(self):
        for cell in self.cells:
            yield [tuple([int(t) for t in cid.split('.')]) for cid in cell]
