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

import sys
import time
import threading

from abc import ABCMeta, abstractmethod
from datetime import datetime

from hf.ui.base import BaseUI
from hf.load import hf
from hf.load import talkusb
from hf.load.routines import throttled
from hf.usb import usbbulk
from hf.usb import usbctrl

class HFSoakInteractive():
  def __init__(self):
    pass

  def start(self, ui, dev):
    self.soak(ui, dev)

  def soak(self, ui, dev):
    while True:
      try:
        time.sleep(1)
        clockrate = ui.prompt_int_single("Clockrate? 1-9 for 100s of MHz, 0=950")
        if clockrate is 0:
          clockrate = 950
        if clockrate < 10:
          clockrate = clockrate*100
        #ui.prompt_enter("Press enter to start board soak with clockrate of "+str(clockrate))
        self.run(ui, dev, clockrate)
      except KeyboardInterrupt:
        ui.log('exiting')
        ui.end()
        return
      except:
        ui.log('Error')

  def run(self, ui, dev, clockrate):
    talkusb.talkusb(hf.INIT, None, 0);
    self.test = throttled.ThrottledRoutine(talkusb.talkusb, clockrate, ui.log, deterministic=False)
    ui.prompt_show("Running at "+str(clockrate)+"MHz. Press board 'RESET' or ctrl+c to end.")
    self.cr = ui.current_round
    self.cr.clockrate = clockrate
    # run soak with temperature monitor
    self.getting_warm = False
    self.throttle = 50
    rslt = True

    # thread
    thread = threading.Thread(target=self.monitor_temp, args={ui})
    self.running = True
    #thread.daemon = True
    thread.start()

    # run
    while rslt:
      if self.getting_warm is False:
        self.throttle -= 1
        if self.throttle < 0:
          self.throttle = 0
      else:
        # getting warm
        self.throttle = 50
        self.getting_warm = False
      rslt = self.test.one_cycle(self.throttle)
    #if rslt is -2:
    #  self.run(ui, dev, clockrate)
    # cycle loop complete
    #ui.prompt_enter("Round Complete. Check temperature.")
    self.running = False

  def monitor_temp(self, ui):
    while self.running:
      time.sleep(0.1)
      self.cr.total_hashes = self.test.stats['hashes']
      self.cr.total_errors = self.test.stats['lhw']
      self.cr.hash_rate    = self.test.stats['hashrate']
      self.cr.stats        = self.test.stats
      if self.test.dies is not None:
        for dinfo in ui.die_info:
          if dinfo is not None:
            die = self.test.dies[dinfo.index]
            if die is not None:
              dinfo.die = die
              dinfo.thermal_cutoff = die['thermal_cutoff']
              dinfo.active = die['active']
              dinfo.pending = die['pending']
              dinfo.temp = die['temperature']
              dinfo.vm = die['core_voltage']
              if dinfo.temp > 104:
                self.getting_warm = True

  def input(self, msg):
    pass

class HFSoakUI(BaseUI):

  def setup_ui(self):
    # column 0
    self.setup_log(   0, 0, w=4)
    # column 4
    self.setup_logo(    4, 1, "HashFast Soak Tool", "v0.1")
    self.setup_input(   4, 8 )
    self.setup_output(  4, 12)
    self.setup_module(  4, 16, nasic=1, coremap=0)
    self.setup_stats(   4, 42)
    # column 9
    self.setup_info(    9, 1 )

  def update_ui(self):
    self.update_module()
    self.update_info()
    self.update_current()

  def refresh_ui(self):
    pass

def main(argv):
  ui = HFSoakUI()
  try:
    ui.setup()
    ui.refresh()

    ui.prompt_show("Please connect device.")
    dev = usbctrl.poll_hf_ctrl_device(printer=ui.log)

    ret = ui.prompt("HashFast Soak Tool. Press 's' to start", "s")
    if ret:
      profiler = HFSoakInteractive()
      profiler.start(ui, dev)

  finally:
    ui.end()

if __name__ == "__main__":
   main(sys.argv[1:])
