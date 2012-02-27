#!/usr/bin/env python

import numpy


def selectivity(responses):
    """
     From: Grunewald and Skoumbourdis (2004)
      The Integration of Multiple Stimulus Features by V1 Neurons
      Journal of Neuroscience 24(41)

    Parameters
    ----------
    responses : array of responses to different things
    """
    responses = numpy.array(responses)
    n = len(responses)
    return (1. - 1. / n * \
            (numpy.sum(responses) ** 2. / numpy.sum(responses ** 2.))) / \
            (1. - 1. / n)
