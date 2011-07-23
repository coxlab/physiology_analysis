#!/usr/bin/env python

import ConfigParser, io, logging, os

# blank items will be filled in later (in set_session)
CFGDEFAULTS = """
[filesystem]
datarepo: /data/raw
tmp: /scratch/tmp
scratch: /scratch
resultsrepo: /data/results
cleanup: True

[pixel clock]
y: -28
h: 2.5
screenh: 137.214
output: 

[audio]
samprate: 44100

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
        
        if self.get('session','output').strip() == '':
            self.set('session','output','/'.join((self.get('filesystem','resultsrepo'),session)))
        
        if self.get('session','scratch').strip() == '':
            self.set('session','scratch','/'.join((self.get('filesystem','scratch'),session)))
        
        if self.get('mworks','file').strip() == '':
            self.set('mworks','file','/'.join((self.get('session','dir'),session + self.get('mworks','ext'))))
        
        if self.get('pixel clock','output').strip() == '':
            self.set('pixel clock','output','/'.join((self.get('session','output'),'pixel_clock')))
