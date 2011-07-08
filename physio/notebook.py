#!/usr/bin/env python

import logging
# logging.basicConfig(level=logging.DEBUG)

import gdata
import gdata.spreadsheet.service

global gdc
gdc = None

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
        config.set('probe','offset',str(offset))
        return offset
    else:
        logging.warning("Failed to find probe[%s] offset[%s]" % (probeID, offsetString))
        return None

def parse_epochs_string(epochsString):
    epochs = []

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
    for k in ['timestamp','username','animal','electrode','descriptionofintent','notes','checklist','stableepochs']:
        returnDict[k] = e.custom[k].text
    
    return returnDict
    