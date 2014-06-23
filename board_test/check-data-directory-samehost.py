#!/usr/bin/env python3

# Copyright (c) 2014 HashFast Technologies LLC

import sys

import boardlib

def usage():
    print("%s data-directory" % (sys.argv[0]))
    sys.exit(1)

if len(sys.argv) != 2:
    usage()

boardlib.valid_datadir_intensive(sys.argv[1], samehost=True)
