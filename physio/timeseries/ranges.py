#!/usr/bin/env python

def overlap(a, b):
    """
    test if two ranges a and b of type (start, stop) overlap
    """
    if (a[0] > b[1]) or (a[1] < b[0]):
        return False
    else:
        return True

def combine(a, b):
    """
    combine two overlapping time ranges
    """
    return [min(a[0],b[0]), max(a[1],b[1])]

def simplify(ranges):
    """
    take a list of time ranges[ranges] and simplify them
    combine all overlaps and sort
    """
    # ranges = list of lists
    simplified = []

    # test if ranges overlap
    for trange in ranges:
        for si in xrange(len(simplified)):
            if overlap(trange, simplified[si]):
                simplified[si] = combine(trange, simplified[si])
                break
        else: # no break was called
            simplified.append(trange)

    # sort
    simplified.sort()

    # recurse until completely simplified
    if len(simplified) == len(ranges):
        return simplified
    else:
        return simplify(simplified)
