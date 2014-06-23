#! /usr/bin/env python3

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
  parser = argparse.ArgumentParser(description='Read and write various settings.')
  parser.add_argument('-r', '--read-die-settings', dest='read_die_settings', action='store_true', help='read die settings')
  parser.add_argument('-w', '--write-die-settings', dest='write_die_settings', type=str, nargs=4, metavar=('DIE:mVLT@FRQ'), help='write die settings')
  return parser.parse_args()

if __name__ == '__main__':
  # parse args before other imports
  args = parse_args()

import sys
from hf.usb import usbbulk
from hf.load import talkusb
from hf.load.routines import settings

def main(args):
  # query device
  dev = usbbulk.poll_hf_bulk_device()
  print (dev.info())
  print (dev.init())

  # Fix: talkusb patch
  talkusb.epr = dev.epr
  talkusb.epw = dev.epw
  #talkusb.talkusb(hf.INIT, None, 0)

  def printmsg(msg):
    print(msg)

  setter = settings.SettingsRoutine(talkusb.talkusb, 1, printmsg)

  if args.read_die_settings:
    setter.global_state = 'read'
    while setter.one_cycle():
      pass

  if args.write_die_settings is not None:
    die_settings = args.write_die_settings
    for die_setting in die_settings:
      die, setting = die_setting.split(':')
      vlt, frq     = setting.split('@')
      setter.setup(int(die), int(frq), int(vlt))
    while setter.one_cycle():
      pass

if __name__ == "__main__":
   main(args)
