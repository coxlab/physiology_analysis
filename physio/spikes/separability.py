#!/usr/bin/env python

import numpy
#import scipy.stats


def reconstruct_from_svd(i, U, vs, V):
    return vs[i] * numpy.outer(U[:, i], V[i])


def separability_correlation(M):
    """
    Test if a response matrix M for feature 1 vs feature 2 is
    separable by...
        1. computing the svd(M) -> U, values, V
        2. attempt to reconstruct M with only values[0] # first singular value
        3. measure correlation between reconstructed M and M (0 -> 1)

    Parameters
    ----------
    M : 2d array : response matrix

    Returns
    -------
    r0, r1 : correlation coefficient between M and prediction from
        singular value 1 (r0) and singular value 2 (r1)

    Notes
    -----
    From: Brincat & Connor (2004)
        Underlying principles of visual shape selectivity in posterior
        inferotemporal cortex. Nature Neuroscience 7(8)
        doi:10.1038/nn1278
    """
    U, vs, V = numpy.linalg.svd(M)
    p0 = reconstruct_from_svd(0, U, vs, V)
    p1 = reconstruct_from_svd(1, U, vs, V)
    r0 = numpy.corrcoef(p0.flatten(), M.flatten())[0, 1]
    r1 = numpy.corrcoef(p1.flatten(), M.flatten())[0, 1]
    return r0, r1


def separability_permutation(M, alpha=0.05, N=None, full=False):
    """
    Parameters
    ----------
    M       : 2d array  : response matrix
    alpha   : float     : probability of type 1 error (false positive)
                            (default = 0.05)
    N       : int       : number of scrambled permutations to test
                            (default = 1 / alpha * 250)
    full    : bool      : return full output (default = False)

    Returns
    -------
    sep : bool : response is/isn't separable
    spi : float : separability index
    (p0, p1) : 2 tuple of floats : p values for singular value
            0 and 1 permutation tests

    Returns if full
    ------
    svs : singular values
    v0s : first singular value for all tested permutations
    v1s : second singular value for all tested permutations

    Notes
    -----
     From: Grunewald and Skoumbourdis (2004)
      The Integration of Multiple Stimulus Features by V1 Neurons
      Journal of Neuroscience 24(41)
    """
    svs0 = numpy.linalg.svd(M, compute_uv=0)
    v0 = svs0[0]
    v1 = svs0[1]

    spi = svs0[0] ** 2. / numpy.sum(svs0[1:] ** 2.)

    # run permutation test
    v0s = []
    v1s = []
    if N is None:
        N = int(1 / alpha * 250)
    for i in xrange(N):
        # scramble M
        # svd
        svs = numpy.linalg.svd( \
                numpy.random.permutation(M.flat).reshape(M.shape), \
                compute_uv=0)
        v0s.append(svs[0])
        v1s.append(svs[1])

    # given v0 and v1, and distributions v0s, v1s, how likely are each
    p0 = sum(v0s > v0) / float(N)
    p1 = sum(v1s > v1) / float(N)

    sep = (p0 < alpha) and (p1 > alpha)

    if full:
        return sep, spi, (p0, p1), svs0, v0s, v1s
    return sep, spi, (p0, p1)
