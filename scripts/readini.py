#!/usr/bin/env python

import logging, sys
import ConfigParser

# logging.basicConfig(level=logging.DEBUG)

usage = "readini.py <file.ini> <section> <variable>"

if len(sys.argv) < 4:
    raise ValueError("sys.argv < 4: %s" % usage)

_, filename, sectionname, variablename = sys.argv[:4]
logging.debug("File    : %s" % filename)
logging.debug("Section : %s" % sectionname)
logging.debug("Variable: %s" % variablename)

parser = ConfigParser.SafeConfigParser()

logging.debug("Reading file")
parser.read(filename)

logging.debug("Getting section/variable")
value = parser.get(sectionname, variablename)

print value