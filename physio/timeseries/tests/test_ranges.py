#!/usr/bin/env python

import physio

def test_simplify(show = False):
    many = []
    sb = physio.timeseries.ranges.simplify # lazy

    def test(b, t):
        r = sb(b)
        if show:
            print "simplifying: %s" % str(b)
            print "\tresult: %s" % str(r)
            print "\ttarget: %s" % str(t)
        assert(r == t)


    # A < B
    b = [[0, 1], [2, 3]]
    test(b, [[0,1],[2,3]])
    many += b

    # A > B
    b = [[2, 3], [0, 1]]
    test(b, [[0,1],[2,3]])
    many += b

    # A over B
    b = [[0, 2], [1, 3]]
    test(b, [[0,3]])
    many += b

    # B over A
    b = [[1, 3], [0, 2]]
    test(b, [[0,3]])
    many += b

    # A in B
    b = [[1, 2], [0, 3]]
    test(b, [[0,3]])
    many += b

    # B in A
    b = [[0, 3], [1, 2]]
    test(b, [[0,3]])
    many += b

    # test many
    test(many, [[0,3]])

    many += [[4, 5],[-2,-1]]
    test(many, [[-2,-1],[0,3],[4,5]])
