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
import csv
from collections import OrderedDict

from abc import ABCMeta, abstractmethod
from datetime import datetime

from hf.ui.base import BaseUI
from hf.load import hf
from hf.load import talkusb
from hf.load.routines import thermal
from hf.load.routines import settings
from hf.usb import usbbulk
from hf.usb import usbctrl

EXP_ASIC = 0.74108
EXP_DIE  = 0.18527

fn = OrderedDict([('die',None),('frequency',None),('voltage',None),('hashrate',None),('hashes',None),('jobs',None),('nonces',None),
                  ('lhw',None),('dhw',None),('chw',None),('temperature',None),('core_voltage',None),('thermal_cutoff',None),('elapsed',None)])

class HFProfilerData:
  def __init__(self):
    pass

class HFProfilerBase(object):
  def __init__(self):
    pass

class HFProfilerInteractive(HFProfilerBase):
  def __init__(self):
    self.frequency = [800]*4
    self.voltage   = [940]*4
    self.csvfilename  = 'surface_{}.csv'.format(int(time.time()))
    with open(self.csvfilename, 'w') as csvfile:
      csvwriter = csv.DictWriter(csvfile, fn, extrasaction='ignore')
      csvwriter.writeheader()

  def start(self, ui, dev):
    talkusb.talkusb(hf.INIT, None, 0);
    self.test(ui, dev)

  def test(self, ui, dev):
    option = ui.prompt_int_single("Option?")
    for frq in [int(x/2) for x in range(800*2, 1050*2, int(12.5*2))]:
      ran_frq = False
      while not ran_frq:
        try:
          time.sleep(1)
          # do settings for this round
          self.frequency = [frq]*4
          self.voltage = [840]*4
          # apply settings
          self.set(ui)
          # run voltage test
          for vlt in range(840, 1050, 5):
            ran_vlt = False
            while not ran_vlt:
              try:
                time.sleep(1)
                self.voltage = [vlt]*4
                # set voltage
                dev = usbctrl.poll_hf_ctrl_device(printer=ui.log)
                ui.log('setting voltage to {}'.format(vlt))
                self.vset(ui, dev)
                # run test
                self.run(ui, dev, option)
                # mark ready for next
                ran_vlt = True
              except KeyboardInterrupt:
                ui.log('exiting')
                ui.end()
                return
              except:
                ui.log("Error in vlt")
          ran_frq = True
        except KeyboardInterrupt:
          ui.log('exiting')
          ui.end()
          return
        except:
          ui.log("Error in frq")


  def set(self, ui):
    ui.prompt_show("Updating Die Settings")
    talkusb.talkusb(hf.INIT, None, 0)
    setter = settings.SettingsRoutine(talkusb.talkusb, 1, ui.log)
    for x in range(4):
      frq = self.frequency[x]
      vlt = self.voltage[x]
      if frq is None or vlt is None:
        return None
      else:
        setter.setup(x, frq, vlt)
    # run
    rslt = True
    while rslt:
      rslt = setter.one_cycle()
    # wait for settings to be applied
    time.sleep(3)

  def vset(self, ui, dev):
    for x in range(4):
      vlt = self.voltage[x]
      dev.voltage_set(0, x, vlt)
      time.sleep(0.1)

  def run(self, ui, dev, option):
    talkusb.talkusb(hf.INIT, None, 0)
    self.test = thermal.ThermalRoutine(talkusb.talkusb, 1, ui.log, deterministic=True)
    ui.prompt_show("Running option "+str(option)+". Press board 'RESET' or ctrl+c to end.")
    ui.next_round()
    self.cr = ui.current_round
    self.cr.clockrate = option
    rslt = True

    # thread
    thread = threading.Thread(target=self.monitor_temp, args={ui})
    self.running = True
    #thread.daemon = True
    thread.start()
    # run
    while rslt:
      rslt = self.test.one_cycle()
      if self.req_stop is True:
        self.test.end()
        rslt = False
    # record current voltage and frequency
    for x in range(4):
      if self.test.dies[x] is not None:
        die = self.test.dies[x]
        if die['voltage'] is not None:
          self.voltage[x] = die['voltage']
        if die['frequency'] is not None:
          self.frequency[x] = die['frequency']
    # write logfile
    with open(self.csvfilename, 'a') as csvfile:
      csvwriter = csv.DictWriter(csvfile, fn, extrasaction='ignore')
      for x in range(4):
        if self.test.dies[x] is not None:
          die = self.test.dies[x]
          csvwriter.writerow(die)
    #if rslt is -2:
    #  self.run(ui, dev, clockrate)
    # cycle loop complete
    #ui.prompt_enter("Round Complete. Check temperature.")
    self.running = False
    # wait for board to reset
    time.sleep(3)

  def monitor_temp(self, ui):
    runtime = 0
    step = 0.5
    self.req_stop = False
    while self.running:
      time.sleep(step)
      runtime += step
      if runtime > 4*60:
        self.req_stop = True
      self.cr.total_hashes = self.test.stats['hashes']
      self.cr.total_errors = self.test.stats['lhw']
      self.cr.hash_rate    = self.test.stats['hashrate']
      if runtime > 20 and self.test.stats['hashes'] < 200*10**9:
        ui.log('req_stop low system hashes')
        self.req_stop = True
      if self.test.dies is not None:
        for dinfo in ui.die_info:
          if dinfo is not None:
            die = self.test.dies[dinfo.index]
            if die is not None:
              dinfo.die = die
              die['voltage'] = self.voltage[dinfo.index]
              dinfo.thermal_cutoff = die['thermal_cutoff']
              dinfo.active = die['active']
              dinfo.pending = die['pending']
              dinfo.temp = die['temperature']
              dinfo.vm = die['core_voltage']

  def input(self, msg):
    pass

class HFProfilerUI(BaseUI):

  def setup_ui(self):
    # column 0
    self.setup_log(   0, 0, w=4)
    # column 4
    self.setup_logo(    4, 1, "HashFast Surface Tool", "v0.1")
    self.setup_input(   4, 8 )
    self.setup_output(  4, 12)
    self.setup_expmodule( 4, 16, coremap=0)
    self.setup_stats(   4, 42)
    # column 9
    self.setup_info(    9, 1 )

  def update_ui(self):
    self.update_module()
    self.update_expmodule()
    self.update_info()
    self.update_current()

  def refresh_ui(self):
    pass

def main(argv):
  ui = HFProfilerUI()
  try:
    ui.setup()
    ui.refresh()

    ui.prompt_show("Please connect device.")
    dev = usbctrl.poll_hf_ctrl_device(printer=ui.log)

    ret = ui.prompt("HashFast Surface Tool. Press 's' to start", "s")
    if ret:
      profiler = HFProfilerInteractive()
      profiler.start(ui, dev)

  finally:
    ui.end()

if __name__ == "__main__":
   main(sys.argv[1:])