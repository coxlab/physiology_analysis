#!/usr/bin/env python

import logging
logging.basicConfig(level = logging.DEBUG)

import physio

parser = OptionParser(usage="usage: %prog [options] sessions...")
# parser.add_option("-b", "--baselineTime", dest = "baselineTime",
#                     help = "number of samples at beginning of recording used to calculate spike threshold",
#                     default = 441000, type='int')
parser.add_option("-f", "--force", dest = "force",
                    help = "force reanalysis",
                    default = False, action = "store_true")
parser.add_option("-v", "--verbose", dest = "verbose",
                    help = "enable verbose reporting",
                    default = False, action = "store_true")
(options, args) = parser.parse_args()

for arg in args:
    session = arg
    logging.debug("Analyzing session: %s" % session)
    try:
        if options.force:
            logging.debug("Forcing reanalysis")
            physio.analysis.analyze.analyze(session)
        else:
            physio.analysis.analyze.analyze(session)
    except Exception as e:
        logging.error("Analysis of session %s failed with %s" % (session, e))
    
    # plotting
    # TODO