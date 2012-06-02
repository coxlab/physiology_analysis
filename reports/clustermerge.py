#!/usr/bin/env python

import collections
import copy

import gdata
import gdata.spreadsheet.service


default_source = 'gdatadict'
email = 'graham@coxlab.org'
password = 'musone'
sheet = 'tsRaBZ--4cFas4ZkTQkaLnQ'

global gdc
gdc = None  # cache client


def get_client(**kwargs):
    global gdc
    if gdc is not None:
        return gdc

    gdc = gdata.spreadsheet.service.SpreadsheetsService()
    gdc.email = kwargs.get('email')
    gdc.password = kwargs.get('password')
    gdc.source = kwargs.get('source', default_source)
    gdc.ProgrammaticLogin()

    return gdc


def get_sheet_as_row_order_dictionary(sheet, ws='default', key=None):
    gdc = get_client()
    lfeed = gdc.GetListFeed(sheet, ws)
    if key is None:
        extract = lambda e: e.custom.copy()
    else:
        extract = lambda e: e.custom[key].text
    r = {}
    for entry in lfeed.entry:
        r[entry.title.text] = extract(entry)
    return r


def get_overrides():
    """
    for sesssion_name, data in overides.iteritems()
    """
    get_client(email=email, password=password)
    return get_sheet_as_row_order_dictionary(sheet)


def check_overrides(overrides):
    for session in overrides.keys():
        parse_merges(overrides[session]['mergeclusters'].text)


def parse_merges(text):
    """
    merge syntax:
        ch.cl=ch.cl
    """
    # blank gdata text is sometimes None
    if text is None:
        return {}
    merges = collections.defaultdict(list)
    for tokens in text.split():
        a, b = tokens.split('=')
        merges[a].append(b)
        merges[b].append(a)
    return dict(merges)


def check_merges(text):
    try:
        merges = parse_merges(text)
        return "Passed", merges
    except Exception as E:
        return "Failed: %s" % E, []


def get_merged(merges, cid, blacklist=None):
    #print "calling get_merged with: %s, %s, %s" % (merges, cid, blacklist)
    if blacklist is None:
        blacklist = []
    if (cid in blacklist) or (cid not in merges):
        return []
    blacklist.append(cid)
    others = []
    for o in merges[cid]:
        if o not in blacklist:
            others.append(o)
            others += get_merged(merges, o, blacklist)
    return others


def merge(cids, merges):
    """
    this needs to take a list of cell ids (ch.cl) and
    a dictionary of merges (key = cell id, value = list of other cell ids)
    and construct a list of lists of (ch, cl) tuples
    """
    used = []
    cells = []
    for mcid in merges.keys():
        if mcid not in cids:
            raise ValueError("Found merge for unknown cell id: %s" % mcid)
    for cid in cids:
        if cid in used:
            continue
        cellids = [cid, ] + get_merged(merges, cid)
        for cellid in cellids:
            if cellid not in cids:
                raise ValueError("Found merge for unknown cell id: %s" \
                        % cellid)
        cells.append(cellids)
        used += cellids
    return cells


def test_merge():
    cids = ['%i.%i' % (ch, cl) for ch in xrange(1, 5) for cl in xrange(2)]
    mtext = '1.0=1.1 1.0=2.0 3.0=4.0'  # should consume 3
    merges = parse_merges(mtext)
    mcids = merge(cids, merges)
    assert len(mcids) == len(cids) - 3

    cids = []
    try:
        mcids = merge(cids, merges)
        raise Exception(\
                "Failed to raise ValueError for merge with unknown cell id")
    except ValueError:
        pass
    return mcids, cids, mtext
