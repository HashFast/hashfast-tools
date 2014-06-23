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

# Running on Debian (sudo may be required):
#   apt-get update
#   apt-get install python-pip
#   pip install --pre pyusb
#   ./ctrltest.py

import sys
import getopt
from hf.usb import usbctrl

def main(argv):
  #
  # usage
  #
  usage  = "usage: ctrltest.py\n"
  usage += "    -f <module>,<fan>,<speed>   set fan speed\n"
  usage += "    -n <name>                   set device name\n"
  usage += "    -o <0/1>                    turn device power off/on\n"
  usage += "    -r [<module>]               reboot into app\n"
  usage += "    -R [<module>]               reboot into loader\n"
  usage += "    -v <module>,<die>,<mvolts>  set die voltage (mV)\n"
  usage += "    -c                          core overview\n"
  usage += "    -e <core>,[<persist>]       enable core\n"
  usage += "    -d <core>,[<persist>]       disable core\n"
  usage += "    -C [<persist>]              clear core map (enable all cores)\n"
  usage += "    -x <core>                   core status\n"
  usage += "    -y <die>                    die status\n"
  usage += "    -z <asic>                   asic status\n"
  # 
  # get opt
  #
  try:
    opts, args = getopt.getopt(argv,"hf:n:o:r:R:v:ce:d:C:x:y:z:")
  except getopt.GetoptError:
    print (usage)
    sys.exit(2)
  # 
  # query device
  #
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
  #
  # parse args
  #
  for opt, arg in opts:
    if   opt == '-h':
      print (usage)
      sys.exit()
    elif opt == '-f':
      module, fan, speed = arg.split(',')
      dev.fan_set(module, fan, speed)
    elif opt == '-n':
      name = arg
      dev.name_set(name)
    elif opt == '-o':
      pass
    elif opt == '-r': # app
      module = arg
      dev.reboot(module, 0x0000)
    elif opt == '-R': # loader
      module = arg
      dev.reboot(module, 0x0001)
    elif opt == '-v':
      module, die, mvolts = arg.split(',')
      dev.voltage_set(module, die, mvolts)
    elif opt == '-c':
      print (dev.core_overview())
    elif opt == '-e':
      if ',' in arg:
        core, persist = arg.split(',')
      else:
        core = arg
        persist = 0
      dev.core_enable(core, persist)
    elif opt == '-d':
      if ',' in arg:
        core, persist = arg.split(',')
      else:
        core = arg
        persist = 0
      dev.core_disable(core, persist)
    elif opt == '-C':
      persist = arg
      dev.core_clear(persist)
    elif opt == '-x':
      core = arg
      print (dev.core_status(core))
    elif opt == '-y':
      die = arg
      t = dev.core_die_status(die)
      print (t)
      print (t.core(0))
      print (t.core(1))
      print (t.core(2))
    elif opt == '-z':
      asic = arg
      print (dev.core_asic_status(asic))

if __name__ == "__main__":
   main(sys.argv[1:])
