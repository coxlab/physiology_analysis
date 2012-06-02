#!/usr/bin/env python

import optparse


def setup_parser(parser=None, query=None):
    if parser is None:
        parser = optparse.OptionParser()
    parser.add_option('-s', '--save', help='save figure',
            default=False, action='store_true')
    return parser
