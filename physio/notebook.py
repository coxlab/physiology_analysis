#!/usr/bin/env python

import logging, sys
# logging.basicConfig(level=logging.DEBUG)

import cfg

import gdata
import gdata.spreadsheet.service

global gdc
gdc = None  # cache client

def get_client(config):
    global gdc
    if not (gdc is None):
        return gdc
    
    gdc = gdata.spreadsheet.service.SpreadsheetsService()
    gdc.email = config.get('gdata','email')
    gdc.password = config.get('gdata','password')
    gdc.source = 'physio_online.notebook'
    logging.debug("gdata connecting")
    gdc.ProgrammaticLogin()
    
    return gdc

def offset_to_float(offsetString):
    if offsetString.strip() == '': return None
    try:
        return float(offsetString)
    except:
        logging.debug("Could not do simple conversion to float: %s" % offsetString)
    for token in offsetString.split():
        try:
            return float(token)
        except:
            logging.debug("Could not convert token to float: %s" % token)
    return None

def lookup_offset(config):
    gdc = get_client(config)
    
    logging.debug("gdata getting electrode list feed")
    listFeed = gdc.GetListFeed(config.get('gdata','probeid'),config.get('gdata','probews'))
    
    probeID = config.get('probe','id').lower()
    offsetString = None
    
    for e in listFeed.entry:
        if e.title.text.lower() == probeID:
            offsetString = e.custom['offset'].text
            break
    
    if offsetString is None:
        logging.warning("Failed to find offset for probe: %s" % probeID)
        return None
    
    offset = offset_to_float(offsetString)
    
    if offset != None:
        #print "Probe: %s Offset: %f" % (probeID, offset)
        logging.debug("Probe: %s Offset: %f" % (probeID, offset))
        #config.set('probe','offset',str(offset))
        return offset
    else:
        logging.warning("Failed to find probe[%s] offset[%s]" % (probeID, offsetString))
        return None

def lookup_probe(config):
    gdc = get_client(config)
    
    logging.debug("gdata getting electrode list feed")
    listFeed = gdc.GetListFeed(config.get('gdata','probeid'),config.get('gdata','probews'))
    
    probeID = config.get('probe','id').lower()
    
    probeEntry = None
    for e in listFeed.entry:
        if e.title.text.lower() == probeID:
            probeEntry = e
            break
    
    if probeEntry is None:
        logging.warning("Probe was not found: %s" % probeID)
        return None
    
    returnDict = {}
    # for k in ['probe_id', 'datereceived', 'ordernumber', 'design', 'thicknessreinforced', 'initialfunctionality',
    #         'boximpedance', 'offset', 'status', 'badsites']:
    for k in probeEntry.custom.keys():
        returnDict[k] = probeEntry.custom[k].text
    
    return returnDict

def timestring_to_seconds(timeString):
    """
    Convert a time string of hh:mm:ss to seconds of type int
    """
    tokens = timeString.split(':')
    if len(tokens) != 3:
        logging.error("Time string was ambiguous: %s" % timeString)
        raise ValueError("Time string was ambiguous: %s" % timeString)
    h, m, s = tokens
    return int(s) + int(m)*60 + int(h)*3600

def parse_epochs_string(epochsString):
    epochs = []
    for line in epochsString.splitlines():
        start, stop = line.split('-')
        start = timestring_to_seconds(start)
        stop = timestring_to_seconds(stop)
        epochs.append((start,stop))
    return epochs

def lookup_session(config):
    """
    Looks up the session data from google docs
    Returns a dict on success, None on failure
    """
    gdc = get_client(config)
    
    logging.debug("gdata getting session list feed")
    listFeed = gdc.GetListFeed(config.get('gdata','notebookid'),config.get('gdata','notebookws'))
    
    session = config.get('session','name')
    
    # convert session date to google format
    animal, dateString = session.split('_')
    if len(dateString) == 8:
        dateString = dateString[2:]
    month = str(int(dateString[2:4]))
    year = str(int('20'+dateString[:2]))
    day = str(int(dateString[4:]))
    gdateString = '/'.join((month,day,year))
    logging.debug("Google Date String: %s" % gdateString)
    animal = animal.lower()
    
    sessionEntry = None
    
    for e in listFeed.entry:
        if e.title.text.split()[0] == gdateString:
            if e.custom['animal'].text.strip().lower() == animal:
                sessionEntry = e
    
    if sessionEntry is None:
        logging.warning("Session was not found: %s" % session)
        return None
    
    # probeID = e.custom['electrode'].text.lower()
    # logging.debug("Found probe: %s" % probeID)
    # if probeID.strip() != '':
    #     logging.debug("Setting probe id based on google data")
    #     config.set('probe','id',probeID)
    #     offset = lookup_offset(config)
    # 
    # epochsString = e.custom['stableepochs'].text
    # logging.debug("Found epochs: %s" % epochsString)
    
    returnDict = {}
    for k in sessionEntry.custom.keys():#['timestamp','username','animal','electrode','descriptionofintent','notes','checklist','stableepochs']:
        returnDict[k] = sessionEntry.custom[k].text
    
    return returnDict


if __name__ == '__main__':
    session = 'K4_110714'
    if len(sys.argv) > 1:
        session = sys.argv[1]
    
    config = cfg.Config()
    config.read_user_config()
    config.set_session(session)
    
    session_dict = lookup_session(config)
    print "Session Dict:", session_dict
    
    config.set('probe','id',session_dict['electrode'].lower().strip())
    probe_dict = lookup_probe(config)
    print "Probe Dict:", probe_dict
