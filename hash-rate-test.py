#!/usr/bin/env python3

# Copyright (c) 2014, HashFast Technologies LLC
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#   1.  Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#   2.  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#   3.  Neither the name of HashFast Technologies LLC nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL HASHFAST TECHNOLOGIES LLC BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

def parse_args():
  parser = argparse.ArgumentParser(description='Run a theoretical hashrate test.')
  parser.add_argument('-c', '--clockrate', dest='clockrate', type=int, default=1, help='clockrate in MHz')
  parser.add_argument('-d', '--deterministic', dest='deterministic', action='store_true', help='run a deterministic test')
  return parser.parse_args()

if __name__ == '__main__':
  # parse args before other imports
  args = parse_args()

import random
import sys
import time
import threading

from hf.load import hf
from hf.load import talkusb
from hf.load.routines import simple

running = False

def main(args):
  global running

  # init talkusb
  talkusb.talkusb(hf.INIT, None, 0)

  def printmsg(msg):
    print(msg)

  # init the test
  test = simple.SimpleRoutine(talkusb.talkusb, args.clockrate, printer=printmsg, deterministic=args.deterministic)

  # thread
  thread = threading.Thread(target=monitor, args={test})
  running = True
  #thread.daemon = True
  thread.start()

  # run the test
  rslt = True
  while rslt:
    rslt = test.one_cycle()

  running = False

  print("All done!")

def monitor(test):
  while running:
    time.sleep(4)
    test.report_hashrate()
    time.sleep(4)
    test.report_errors()

if __name__ == "__main__":
   main(args)
