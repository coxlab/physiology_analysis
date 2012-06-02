#!/usr/bin/env python

import ast
import logging
import sys

import tables
import gdata
import gdata.spreadsheet.service

import physio

# get all of this from gdata, write to all session files
# root.Events._v_attrs['CNC_OFFSET'] (int)
# root.Events._v_attrs['EYETRACKER_OFFSET'] (int)
# root.Events._v_attrs['LOCATION'] (list of float)

default_source = 'gdatadict'
#fake = True  # fake write, is set inside main
#whitelist = ['M2_120525', 'M2_120529']
email = 'graham@coxlab.org'
password = 'musone'
sheet = 'tsRaBZ--4cFas4ZkTQkaLnQ'

default_plugs = [
        ('location', lambda f: f.root.Events, 'LOCATION', \
                lambda i: ast.literal_eval(i.text)),
        ('cncoffset', lambda f: f.root.Events, 'CNC_OFFSET', \
                lambda i: int(i.text)),
        ('eyetrackeroffset', lambda f: f.root.Events, 'EYETRACKER_OFFSET', \
                lambda i: int(i.text)),
        ]

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
    get_client(email=email, password=password)
    return get_sheet_as_row_order_dictionary(sheet)


def process_plugs(plugs, whitelist, fake):
    overrides = get_overrides()
    for (session_name, data) in overrides.iteritems():
        if (not len(whitelist)) or (session_name in whitelist):
            try:
                cfg = physio.cfg.load(session_name)
                n_epochs = physio.session.get_n_epochs(session_name)
                for epoch_index in xrange(n_epochs):
                    epoch_dir = physio.session.get_epoch_dir(cfg, epoch_index)
                    fn = epoch_dir + '/' + session_name + '.h5'
                    if not fake:
                        f = tables.openFile(fn, 'a')
                        for (co, node, key, conv) in plugs:
                            node(f)._v_attrs[key] = conv(data[co])
                        f.flush()
                        f.close()
                    else:
                        for (co, node, key, conv) in plugs:
                            logging.debug("Writing %s to %s, %s" \
                                    % (conv(data[co]), session_name, key))
            except Exception as E:
                logging.error("Failed to write to session %s: %s" % \
                        (session_name, E))

if __name__ == '__main__':
    args = sys.argv[1:]
    if '-f' in args:
        fake = True
        logging.basicConfig(level=logging.DEBUG)
        args.remove('-f')
    else:
        fake = False
        logging.basicConfig(level=logging.ERROR)
    whitelist = args
    process_plugs(default_plugs, whitelist, fake)
