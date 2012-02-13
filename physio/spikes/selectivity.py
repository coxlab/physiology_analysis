#!/usr/bin/env python

import numpy

def selectivity(responses):
    """
    Parameters
    ----------
    responses : array of responses to different things
    """
    responses = numpy.array(responses)
    n = len(responses)
    return (1. - 1./n * \
            (numpy.sum(responses)**2. / numpy.sum(responses ** 2.))) / \
            (1. - 1./n)
