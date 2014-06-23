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
  parser = argparse.ArgumentParser(description='Talk to a HashFast board over USB control channel.')
  parser.add_argument('-f', '--fan',          dest='fan',         type=int, nargs=3, metavar=('MODULE', 'FAN', 'SPEED'), help='set fan speed')
  parser.add_argument('-n', '--name',         dest='name',        type=str, help='set device name')
  parser.add_argument('-o', '--power',        dest='power',       type=int, metavar='0/1', help='turn device power off/on')
  parser.add_argument('-r', '--app',          dest='reboot_app',  type=int, metavar='MODULE', help='reboot into app')
  parser.add_argument('-R', '--loader',       dest='reboot_load', type=int, metavar='MODULE', help='reboot into loader')
  parser.add_argument('-v', '--voltage',      dest='voltage',     type=int, nargs=3, metavar=('MODULE', 'DIE', 'MILLIVOLTS'), help='set die voltage')
  parser.add_argument('-c', '--cores',        dest='cores',       action='store_true', help='core_overview')
  parser.add_argument('-e', '--core-enable',  dest='core_enable', type=int, nargs=2, metavar=('CORE', 'PERSIST'), help='core enable')
  parser.add_argument('-d', '--core-disable', dest='core_disable',type=int, nargs=2, metavar=('CORE', 'PERSIST'), help='core disable')
  parser.add_argument('-C', '--clear',        dest='core_clear',  type=int, metavar='PERSIST', help='clear core map (enable all cores)')
  parser.add_argument('-x', '--core-status',  dest='core_status', type=int, metavar='CORE', help='core status')
  parser.add_argument('-y', '--die-status',   dest='die_status',  type=int, metavar='DIE', help='die stats')
  parser.add_argument('-z', '--asic-status',  dest='asic_status', type=int, metavar='ASIC', help='asic status')
  return parser.parse_args()

if __name__ == '__main__':
  # parse args before other imports
  args = parse_args()

import sys
from hf.usb import usbctrl

def main(args):
  # query device
  dev = usbctrl.HFCtrlDevice()
  print (dev.info())
  print (dev.status())
  config = dev.config()
  print (config)
  print (dev.name())
  for module in range(config.modules):
    print (dev.version(module))
    print (dev.serial(module))
    print (dev.power(module))
    print (dev.fan(module))

  if args.fan is not None:
    module, fan, speed = args.fan
    dev.fan_set(module, fan, speed)

  if args.name is not None:
    name = args.name
    dev.name_set(name)

  if args.power is not None:
    pass

  if args.reboot_app is not None:
    module = args.reboot_app
    dev.reboot(module, 0x0000)

  if args.reboot_load is not None:
    module = args.reboot_load
    dev.reboot(module, 0x0001)

  if args.voltage is not None:
    module, die, mvolts = args.voltage
    dev.voltage_set(module, die, mvolts)

  if args.cores:
    print (dev.core_overview())

  if args.core_enable is not None:
    core, persist = args.core_enable
    dev.core_enable(core, persist)

  if args.core_disable is not None:
    core, persist = args.core_disable
    dev.core_disable(core, persist)

  if args.core_clear is not None:
    persist = args.core_clear
    dev.core_clear(persist)

  if args.core_status is not None:
    core = args.core_status
    print (dev.core_status(core))

  if args.die_status is not None:
    die = args.die_status
    t = dev.core_die_status(die)
    print (t)

  if args.asic_status is not None:
    asic = args.asic_status
    print (dev.core_asic_status(asic))

if __name__ == "__main__":
   main(args)
