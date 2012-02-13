#!/usr/bin/env python

import numpy
import scipy.stats

def measure_bin_significance(baseline, binned_responses):
    """
    Test which bins in a array of binned responses differ
    significantly from the baseline (using a related sampled ttest)

    Parameters
    ----------
    baseline : 1d array of binned baseline responses
    binned_responses : 2d array of binned responses

    Returns
    -------
    significant_bins : list of p-values for each response bin
    """
    return [scipy.stats.ttest_rel(baseline, b)[1] \
            for b in binned_responses.T]

def measure_binned_latency(baseline, binned_responses, alpha = 0.001):
    ps = numpy.array(measure_bin_significance(baseline, binned_responses))
    return numpy.where(ps < alpha)[0]
