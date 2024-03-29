#!/usr/bin/env python

import ConfigParser, io, logging, os

# blank items will be filled in later (in set_session)
CFGDEFAULTS = """
[filesystem]
rawrepo: /data/raw
datarepo: /data/raw
tmp: /scratch/tmp
scratch: /scratch
resultsrepo: /data/results
cleanup: True
atlas: /atlas

[clustering]
options:
njobs: 8
nadjacent: 0

[pixel clock]
threshold: 0.03
refractory: 44
mincodetime: 441
y: -28
height: 8.5
screenh: 64.54842055808264
sepratio: 0.2
minmatch: 10
maxerr: 0
regex: pixel_clock([0-9])#[0-9]+\.wav

[audio]
samprate: 44100
regex: input_([0-9])#[0-9]+\.wav

[mworks]
ext: .h5
file: 

[epochs]
timeunit: mworks
settletime: 300

[session]
name: 
dir: 
scratch: 
output: 
outputprefix: 

[probe]
id: 
offset: 

[gdata]
probeid: tFAlHPctqL5YNf1oocFPLgA
probews: od6
notebookid: tHR87keGRC4XIZlX6uWi-vA
notebookws: od6
email:
password:
"""

def load(session, customCfgFile = None):
    config = Config()
    config.read_user_config()
    config.read_session_config(session)
    config.set_session(session)
    if not customCfgFile is None: config.read(customCfgFile)
    return config

class Config(ConfigParser.SafeConfigParser):
    def __init__(self, *args, **kwargs):
        ConfigParser.SafeConfigParser.__init__(self, *args, **kwargs)
        # read in defaults
        self.readfp(io.BytesIO(CFGDEFAULTS))
    
    def read_user_config(self, homeDir=os.getenv('HOME')):
        filename = '/'.join((homeDir,'.physio'))
        if os.path.exists(filename):
            logging.debug("Found user cfg: %s" % filename)
            self.read(filename)
        else:
            logging.warning('No user cfg found: %s' % filename)
    
    def read_session_config(self, session):
        filename = '/'.join((self.get('filesystem','datarepo'),session,'physio.ini'))
        if os.path.exists(filename):
            logging.debug("Found session cfg: %s" % filename)
            self.read(filename)
        else:
            logging.warning('No session cfg found: %s' % filename)
    
    def set_session(self, session):
        self.set('session','name',session)
        
        if self.get('session','dir').strip() == '':
            self.set('session','dir','/'.join((self.get('filesystem','datarepo'),session)))
        
        if self.get('session','outputprefix').strip() == '':
            self.set('session','outputprefix','/'.join((self.get('filesystem','resultsrepo'),session)))
        
        if self.get('session','scratch').strip() == '':
            self.set('session','scratch','/'.join((self.get('filesystem','scratch'),session)))
        
        if self.get('mworks','file').strip() == '':
            self.set('mworks','file','/'.join((self.get('session','dir'),session + self.get('mworks','ext'))))
        
        # if self.get('pixel clock','scratch').strip() == '':
        #     self.set('pixel clock','scratch','/'.join((self.get('session','scratch'),'pixel_clock')))
    
    def set_epoch(self, audioTimerange):
        epochDir = "%s/%i_%i" % (self.get('session','outputprefix'), int(audioTimerange[0]), int(audioTimerange[1]))
        self.set('session','output',epochDir)
