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

from collections        import OrderedDict
from abc                import ABCMeta, abstractmethod
from datetime           import datetime

from hf.ui.base         import BaseUI
from hf.load            import hf
from hf.load            import talkusb
from hf.load.routines   import settings
from hf.load.routines   import thermal
from hf.usb             import usbbulk
from hf.usb             import usbctrl

FRQ_MIN  = 925
FRQ_MAX  = 1000
FRQ_STEP = 12.5
FRQS = [int(x/2) for x in range(FRQ_MIN*2, FRQ_MAX*2, int(FRQ_STEP*2))]

VLT_MIN  = 900
VLT_MAX  = 1020
VLT_STEP = 5
VLTS = [x for x in range(VLT_MIN, VLT_MAX, VLT_STEP)]

fn = OrderedDict([('die',None),('frequency',None),('voltage',None),('hashrate',None),('hashes',None),('jobs',None),('nonces',None),
                  ('lhw',None),('dhw',None),('chw',None),('temperature',None),('core_voltage',None),('thermal_cutoff',None),('elapsed',None),
                  ('moving_hashes',None),('moving_hashrate',None),('moving_noncerate',None),('moving_lhwrate',None),('moving_dhwrate',None)])

class HFProfilerData:
  def __init__(self):
    pass

class HFProfilerBase(object):
  def __init__(self):
    pass

class HFProfilerInteractive(HFProfilerBase):
  def __init__(self):
    self.frequency = [None]*4
    self.voltage   = [None]*4
    self.recommend = [ [] for x in range(4)]
    self.csvfilename  = 'auto_profiler_{}.csv'.format(int(time.time()))
    with open(self.csvfilename, 'w') as csvfile:
      csvwriter = csv.DictWriter(csvfile, fn, extrasaction='ignore')
      csvwriter.writeheader()

  def start(self, ui, dev):
    talkusb.talkusb(hf.INIT, None, 0);
    self.test(ui, dev)
    self.confirm(ui)
    ui.prompt_enter("Check Die Settings on Left")

  def test(self, ui, dev):
    disabled_die = ui.prompt_int_single("Disabled Die? 0-3, 4=NO")
    #option = ui.prompt_int_single("Option?")
    for frq in FRQS:
      ran_frq = False
      while not ran_frq:
        try:
          self.running = False
          time.sleep(1)
          # do settings for this round
          self.frequency = [frq]*4
          self.voltage = [VLT_MIN]*4
          if disabled_die <= 3:
            #self.frequency[disabled_die] = 0
            self.voltage[disabled_die]   = 0
          # apply settings
          self.set(ui)
          # get dev
          dev = usbctrl.poll_hf_ctrl_device(printer=ui.log)
          # run test
          self.run(ui, dev, frq)
          # mark ready for next
          ran_frq = True

          self.confirm(ui)

        except KeyboardInterrupt:
          ui.log('exiting')
          ui.end()
          return
        except:
          ui.log("Error in frq")
          ui.log("ex: (%s, %s, %s)" % (sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
          time.sleep(10)

  def confirm(self, ui):
    for di, drecommend in enumerate(self.recommend):
      for r in drecommend:
        ui.log("{0} mV @ {1} MHz: {2:6.2f}".format(r['vlt'], r['frq'], r['sm']['hashrate']/10**9))
      ui.log("Die {}".format(di))

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
    self.test = thermal.ThermalRoutine(talkusb.talkusb, option, ui.log, deterministic=True)
    ui.prompt_show("Running option "+str(option)+". Press board 'RESET' or ctrl+c to end.")
    ui.current_round.clockrate = option
    rslt = True

    self.run_stats = [ [{'die':x, 'frq':option, 'vlt':vlt, 'sm':None, 'em':None, 's':False, 'c':False} for vlt in VLTS] for x in range(4)]

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
    #####self.record()
    # cycle loop complete
    self.running = False
    # wait for board to reset
    time.sleep(3)

  def record(self):
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


  def monitor_temp(self, ui):
    runtime = 0
    self.req_stop = False
    die_stops = [False for x in range(4)]
    run_stats = self.run_stats
    # get dev
    dev = usbctrl.poll_hf_ctrl_device(printer=ui.log)
    # wait for init
    time.sleep(5)
    # monitor
    while self.running:
      try:
        # time
        loop_time = 0.4
        time.sleep(loop_time)
        runtime += loop_time
        if runtime > 4*60: # 4 minutes
          self.req_stop = True
        # die voltage
        for di, drs in enumerate(run_stats):
          this_die = self.test.dies[di]
          if this_die['moving'] is None:
            continue
          #if die_stops[di] is True:
          #  continue
          current_mv = this_die['moving'][-1]
          for ri, rs in enumerate(drs):
            if rs['s'] is False:
              dev.voltage_set(0, di, rs['vlt'])
              ui.next_round_die(di, True)
              self.voltage[di] = rs['vlt']
              rs['s'] = True
              rs['sm'] = current_mv
              break
            if rs['c'] is False:
              if rs['sm'] is not current_mv:
                ######
                ## Record to CSV
                ######
                # write logfile
                with open(self.csvfilename, 'a') as csvfile:
                  this_die['moving_hashes']     = current_mv['hashes']
                  this_die['moving_hashrate']   = current_mv['hashrate']
                  this_die['moving_noncerate']  = current_mv['noncerate']
                  this_die['moving_lhwrate']    = current_mv['lhwrate']
                  this_die['moving_dhwrate']    = current_mv['dhwrate']
                  csvwriter = csv.DictWriter(csvfile, fn, extrasaction='ignore')
                  csvwriter.writerow(this_die)
                ###
                ###
                rs['em'] = current_mv
                rs['c'] = True
                if rs['sm']['hashrate'] > 100*10**9 and (rs['em']['lhwrate'] >= rs['sm']['lhwrate'] or rs['em']['dhwrate'] >= rs['sm']['dhwrate']):
                  # recommend the last operating point
                  prev_rs = drs[(ri - 1)]
                  self.recommend[di].append(prev_rs)
                  # stop testing this die
                  die_stops[di] = True
                else:  
                  continue
              else:
                break
        for die_stop in die_stops:
          if die_stop is False:
            break
          self.req_stop = True
        # ui stats
        ui.current_round.total_hashes = self.test.stats['hashes']
        ui.current_round.total_errors = self.test.stats['lhw']
        ui.current_round.hash_rate    = self.test.stats['hashrate']
        ui.current_round.stats        = self.test.stats
        if self.test.dies is not None:
          for dinfo in ui.die_info:
            if dinfo is not None:
              die = self.test.dies[dinfo.index]
              if die is not None:
                dinfo.die = die
                if self.voltage[dinfo.index] is not None:
                  die['voltage'] = self.voltage[dinfo.index]
                dinfo.thermal_cutoff = die['thermal_cutoff']
                dinfo.active = die['active']
                dinfo.pending = die['pending']
                dinfo.temp = die['temperature']
                dinfo.vm = die['core_voltage']
      except:
        ui.log('exception in thread')

  def input(self, msg):
    pass

class HFProfilerUI(BaseUI):

  def setup_ui(self):
    # column 0
    self.setup_log(   0, 0, w=4)
    # column 4
    self.setup_logo(    4, 1, "HashFast Profiling Tool", "v0.1")
    self.setup_input(   4, 8 )
    self.setup_output(  4, 12)
    self.setup_expmodule( 4, 16, coremap=False)
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

    ret = ui.prompt("HashFast Profiling Tool. Press 's' to start", "s")
    if ret:
      profiler = HFProfilerInteractive()
      profiler.start(ui, dev)

  finally:
    ui.end()

if __name__ == "__main__":
   main(sys.argv[1:])