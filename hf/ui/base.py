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

import curses
import threading
import time
import sys

from datetime     import datetime
from abc          import ABCMeta, abstractmethod
from collections  import deque

from ..util       import with_metaclass

EXP_ASIC = 0.74108
EXP_DIE  = 0.18527


CWIDTH = 12

def ctx(col):
  return col*(CWIDTH)

def wtx(width):
  return width*(CWIDTH)

class RoundInfo:
  def __init__(self):
    self.clockrate = 0
    self.total_hashes = 0
    self.total_errors = 0
    self.hash_rate = 0
    self.stats = None

class DieInfo:
  def __init__(self, index, coremap):
    self.index    = index
    self.coremap  = coremap
    self.throttle = 0
    self.active   = 0
    self.pending  = 0
    self.temp     = 0
    self.thermal_cutoff = 0
    self.vm       = 0
    self.va       = 0
    self.vb       = 0
    self.vc       = 0
    self.vd       = 0
    self.ve       = 0
    self.die      = None

class BaseUI(with_metaclass(ABCMeta, object)):

  @abstractmethod
  def setup_ui(self):
    pass

  @abstractmethod
  def update_ui(self):
    pass

  @abstractmethod
  def refresh_ui(self):
    pass

  def __init__(self):
    # setup curses window
    self.screen = curses.initscr()
    self.wlogo = None
    self.wmodule = None
    self.wasic = [None]*5
    self.wdie = [None]*5*4
    self.wexpdie = [None]*4
    self.winfo = None
    self.log_buffer = deque(["Log Start"])
    self.wlog = None
    self.winput = None
    self.woutput = None
    self.wprevious = None
    self.wstats = None
    # device information
    #self.connected_die
    self.die_info = [None]*5*4
    self.current_round = RoundInfo()

  def setup_logo(self, c, y, name, version):
    self.wlogo = curses.newwin(7, 60, y, ctx(c))
    #self.wlogo.bkgd(' ', curses.color_pair(4))
    self.wlogo.addstr(0,0,"______  __             ______ __________             _____ ")
    self.wlogo.addstr(1,0,"___  / / /_____ __________  /____  ____/_____ _________  /_")
    self.wlogo.addstr(2,0,"__  /_/ /_  __ `/_  ___/_  __ \_  /_   _  __ `/_  ___/  __/")
    self.wlogo.addstr(3,0,"_  __  / / /_/ /_(__  )_  / / /  __/   / /_/ /_(__  )/ /_  ")
    self.wlogo.addstr(4,0,"/_/ /_/  \__,_/ /____/ /_/ /_//_/      \__,_/ /____/ \__/  ")
    self.wlogo.addstr(5,1, name)
    self.wlogo.addstr(5,50,version)
    self.wlogo.addstr(6,0,"                                          (c) 2014 HashFast")

  def setup_colors(self):
    curses.start_color()
    #0:black, 1:red, 2:green, 3:yellow, 4:blue, 5:magenta, 6:cyan, and 7:white
    #curses.init_pair(0, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair( 1, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair( 2, curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair( 3, curses.COLOR_WHITE, curses.COLOR_YELLOW)
    curses.init_pair( 4, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair( 5, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
    curses.init_pair( 6, curses.COLOR_WHITE, curses.COLOR_CYAN)
    ## Black Text on Colored Background
    curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(12, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(13, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(14, curses.COLOR_BLACK, curses.COLOR_BLUE)
    curses.init_pair(15, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    curses.init_pair(16, curses.COLOR_BLACK, curses.COLOR_CYAN)
    ## Red Text on Colored Background
    curses.init_pair(20, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(21, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(22, curses.COLOR_RED, curses.COLOR_GREEN)
    curses.init_pair(23, curses.COLOR_RED, curses.COLOR_YELLOW)
    curses.init_pair(24, curses.COLOR_RED, curses.COLOR_BLUE)
    curses.init_pair(25, curses.COLOR_RED, curses.COLOR_MAGENTA)
    curses.init_pair(26, curses.COLOR_RED, curses.COLOR_CYAN)

  def setup_module(self, c, y, w=10, nasic=1, coremap=True):
    if nasic > 5:
      raise Exception("Cannot display more than 5 ASICs")
    self.wmodule = curses.newwin(26, wtx(w), y, ctx(c))
    self.wmodule.bkgd(' ', curses.color_pair(10))
    dx = int(int(wtx(w) - wtx(2)*nasic)/2)
    print(str(dx))
    for asic in range(nasic):
      self.setup_asic(asic, 0, dx, coremap)
      dx += wtx(2)

  def setup_asic(self, asic, yo, xo, coremap):
    self.wasic[asic] = self.wmodule.derwin(26, 22, yo, xo)
    fdie = 0 + 4*asic
    if coremap:
      for d in range(fdie, fdie+4):
        if d % 4 == 0:
          self.setup_die(asic, d, 0, 0, coremap)
        if d % 4 == 1:
          self.setup_die(asic, d, 0, 11, coremap)
        if d % 4 == 2:
          self.setup_die(asic, d, 13, 11, coremap)
        if d % 4 == 3:
          self.setup_die(asic, d, 13, 0, coremap)
    else:
      for d in range(fdie, fdie+4):
        if d % 4 == 1: # 0:
          self.setup_die(asic, d, 0, 0, coremap)
        if d % 4 == 2: # 1:
          self.setup_die(asic, d, 0, 11, coremap)
        if d % 4 == 3: # 2:
          self.setup_die(asic, d, 13, 11, coremap)
        if d % 4 == 0: # 3:
          self.setup_die(asic, d, 13, 0, coremap)

  def setup_die(self, asic, die, y, x, coremap):
    self.wdie[die] = self.wasic[asic].derwin(13, 11, y, x)
    self.die_info[die] = DieInfo(die, coremap)
    self.wdie[die].bkgd(' ',curses.color_pair(10))
    self.wdie[die].box()
    if coremap:
      dstr = "D"+str(die)
    else:
      dstr = "D"+str(die+1)
    self.wdie[die].addstr(0,0,dstr)
    if die % 4 == 0:
      self.wdie[die].addstr(12,0,"USB",curses.color_pair(3))

  def setup_info(self, c, y, w=5):
    self.winfo = curses.newwin(8, wtx(w), y, ctx(c))
    self.winfo.box()
    self.winfo.addstr(0,0,"INFORMATION")
    self.winfo.addstr(1,1,"START")
    self.winfo.addstr(2,4,str(datetime.now()))
    self.winfo.addstr(3,1,"UPDATED")
    self.winfo.addstr(4,4,str(datetime.now()))

  def setup_log(self, c, y, w=2, h=100):
    self.wlog = curses.newwin(h, wtx(w), y, ctx(c))
    self.wlog.box()
    self.wlog.addstr(0,0,"LOG")

  def setup_input(self, c, y, w=10):
    self.winput = curses.newwin(4, wtx(w), y, ctx(c))
    self.winput.bkgd(' ',curses.color_pair(6))
    self.winput.box()
    self.winput.addstr(0,0,"INPUT")

  def setup_output(self, c, y, w=10):
    self.woutput = curses.newwin(4, wtx(w), y, ctx(c))
    self.woutput.bkgd(' ',curses.color_pair(2))
    self.woutput.box()
    self.woutput.addstr(0,0,"CURRENT")
    self.woutput.addstr(1,2,"FREQUENCY")
    self.woutput.addstr(1,20,"VOLTAGE")
    self.woutput.addstr(1,40,"HASHRATE")
    self.woutput.addstr(1,60,"LHW ERRORS")
    self.woutput.addstr(1,80,"DHW ERRORS")

  def setup_previous(self, c, y, w=10):
    self.wprevious = curses.newwin(60, wtx(w), y, ctx(c))
    #wprevious.bkgd(' ',curses.A_DIM)
    self.wprevious.box()
    self.wprevious.addstr(0,0,"PREVIOUS")
    self.wprevious.addstr(1,2,"FREQUENCY")
    self.wprevious.addstr(1,20,"VOLTAGE")
    self.wprevious.addstr(1,40,"HASHRATE")
    self.wprevious.addstr(1,60,"LHW ERRORS")
    self.wprevious.addstr(1,80,"DHW ERRORS")

  def setup_expmodule(self, c, y, w=10, coremap=True):
    self.wmodule = curses.newwin(26, wtx(w), y, ctx(c))
    self.wmodule.bkgd(' ', curses.color_pair(10))
    asic = 0
    self.setup_asic(asic, 0, ctx(4), coremap)
    if coremap:
      for d in range(4):
        if d % 4 == 0:
          self.setup_expdie(c,    y+0,  die=d)
        if d % 4 == 1:
          self.setup_expdie(c+6,  y+0,  die=d)
        if d % 4 == 2:
          self.setup_expdie(c+6,  y+13, die=d)
        if d % 4 == 3:
          self.setup_expdie(c,    y+13, die=d)
    else:
      for d in range(4):
        if d % 4 == 1: # 0:
          self.setup_expdie(c,    y+0,  die=d)
        if d % 4 == 2: # 1:
          self.setup_expdie(c+6,  y+0,  die=d)
        if d % 4 == 3: # 2:
          self.setup_expdie(c+6,  y+13, die=d)
        if d % 4 == 0: # 3:
          self.setup_expdie(c,    y+13, die=d)

  def setup_stats(self, c, y, w=10):
    self.wstats = curses.newwin(4, wtx(w), y, ctx(c))
    self.wstats.bkgd(' ',curses.color_pair(5))
    self.wstats.box()
    self.wstats.addstr(0,0,"STATS")
    self.wstats.addstr(1,2,"ENABLED")
    self.wstats.addstr(1,20,"DISABLED")
    self.wstats.addstr(1,40,"INFLIGHT")
    self.wstats.addstr(1,60,"ACTIVE")
    self.wstats.addstr(1,80,"PENDING")

  def setup(self):
    self.setup_colors()
    try:
      self.setup_ui()
    finally:
      # thread
      self.thread = threading.Thread(target=self.run_update)
      self.thread.daemon = True
      self.thread.start()

  def update_log(self):
    while len(self.log_buffer):
      msg = self.log_buffer.popleft()
      self.wlog.move(1,1)
      self.wlog.insertln()
      self.wlog.addstr(1,1,msg)
    self.wlog.box()
    self.wlog.addstr(0,0,"LOG")

  def update_info(self):
    self.winfo.addstr(4,4,"{}".format(datetime.now()))

  def update_current(self):
    cr = self.current_round
    if cr.stats is not None:
      self.woutput.addstr(2,2,"{}".format(cr.clockrate))
      vlt = []
      for di in self.die_info:
        if di is not None:
          dd = di.die
          if dd is not None:
            vlt.append(dd['voltage'])
      if len(vlt) >= 4:
        self.woutput.addstr(2,20,"[{0} {1} {2} {3}]".format(*vlt))
      self.woutput.addnstr(2,40,"{0:3.2f}GH/s".format(cr.stats['hashrate'] / 10**9),10)
      self.woutput.addstr(2,60,"{}".format(cr.stats['lhw']))
      self.woutput.addstr(2,80,"{}".format(cr.stats['dhw']))

  def update_expmodule(self):
    die_count = len(self.wdie)
    for die, wexpdie in enumerate(self.wexpdie):
      if wexpdie is not None:
        self.update_expdie(die)

  def next_round(self):
    die_count = len(self.wdie)
    for die, wexpdie in enumerate(self.wexpdie):
      if wexpdie is not None:
        wexpdie.move(1,0)
        wexpdie.insertln()

  def next_round_die(self, n, moving=False):
    wexpdie = self.wexpdie[n]
    if wexpdie is not None:
      if moving:
        di = self.die_info[n]
        dd = di.die
        if dd is not None and dd['moving'] is not None:
          mv = dd['moving'][-1]
          nonces = mv['noncerate']
          if nonces is 0:
            nonces = 1
          wexpdie.addnstr(1,17,"{0:07d}".format(int(mv['hashes'] / 10**9)),7)
          wexpdie.addnstr(1,26,"{0:03.2f}".format(mv['hashrate'] / 10**9),6)
          wexpdie.addnstr(1,34,".{0:04d}".format(int(mv['lhwrate']*1000/nonces)),5)
          wexpdie.addnstr(1,41,".{0:04d}".format(int(mv['dhwrate']*1000/nonces)),5)
      wexpdie.move(1,0)
      wexpdie.insertln()

  def setup_expdie(self, c, y, w=4, die=0):
    self.wexpdie[die] = curses.newwin(13, wtx(w), y, ctx(c))
    self.wexpdie[die].bkgd(' ', curses.color_pair(10))
    #self.wexpdie[die].box()
    #self.wexpdie[die].addstr(0,0,"D"+str(die))
    self.wexpdie[die].addstr(0,0,"FRQ", curses.A_UNDERLINE)
    self.wexpdie[die].addstr(0,4," mV", curses.A_UNDERLINE)
    self.wexpdie[die].addstr(0,8," EXP  ", curses.A_UNDERLINE)
    self.wexpdie[die].addstr(0,17,"GHASHES", curses.A_UNDERLINE)
    self.wexpdie[die].addstr(0,26," GH/S ", curses.A_UNDERLINE)
    self.wexpdie[die].addstr(0,34,"LHW/N", curses.A_UNDERLINE)
    self.wexpdie[die].addstr(0,41,"DHW/N", curses.A_UNDERLINE)

  def update_expdie(self, n):
    di = self.die_info[n]
    dd = di.die
    wexpdie = self.wexpdie[n]
    if dd is not None:
      nonces = dd['nonces']
      if nonces is 0:
        nonces = 1
      wexpdie.addnstr(1,0,"{0:03d}".format(int(dd['frequency'])),3)
      wexpdie.addnstr(1,4,"{0:03d}".format(int(dd['voltage'])),3)
      wexpdie.addnstr(1,8,"{0:03.2f}".format(dd['frequency']*EXP_DIE),6)
      wexpdie.addnstr(1,17,"{0:07d}".format(int(dd['hashes'] / 10**9)),7)
      wexpdie.addnstr(1,26,"{0:03.2f}".format(dd['hashrate'] / 10**9),6)
      wexpdie.addnstr(1,34,".{0:04d}".format(int(dd['lhw']*1000/nonces)),5)
      wexpdie.addnstr(1,41,".{0:04d}".format(int(dd['dhw']*1000/nonces)),5)

  def update_module(self):
    die_count = len(self.wdie)
    for die, wdie in enumerate(self.wdie):
      if wdie is not None:
        self.update_die(die)

  def update_die(self, n):
    di = self.die_info[n]
    dd = di.die
    wdie = self.wdie[n]
    if dd is not None:
      # temperature
      temp = int(di.temp)
      if temp < 85:
        color = curses.color_pair(2)
      elif temp < 95:
        color = curses.color_pair(3)
      else:
        color = curses.color_pair(1)
      if di.coremap:
        for y in range(0,11):
          for x in range(0,9):
            if True: #die_status.core_xy(n,xy)[0]:
              wdie.addstr(y+1,x+1,'x')
        if n%4 == 0 or n%4 == 1:
          wdie.addstr(1, 4, "{0:03d}".format(temp), color)
        else:
          wdie.addstr(11,4, "{0:03d}".format(temp), color)
        # voltages
        color = curses.color_pair(0)
        #wdie.addstr(0, 4, "{0:03d}".format(di.vm), color)
        #wdie.addstr(0, 8, "{0:03d}".format(di.va), color)
        #wdie.addstr(12,0, "{0:03d}".format(di.vb), color)
        #wdie.addstr(12,4, "{0:03d}".format(di.vc), color)
        #wdie.addstr(12,8, "{0:03d}".format(di.vd), color)
      else:
        temp_row = 6
        if n%4 == 1 or n%4 == 2:
         #wdie.addstr(1, 1,"SQ    {0:02d}%".format(int(di.throttle)))
          wdie.addstr(1, 1,"ACT    {0:02d}".format(di.active))
          wdie.addstr(2, 1,"PEND   {0:02d}".format(di.pending))
          wdie.addstr(3, 1,"LHW  {0:04d}".format(dd['lhw']))
          wdie.addstr(4, 1,"DHW  {0:04d}".format(dd['dhw']))
          wdie.addstr(5, 1,"NNC  {0:04d}".format(dd['nonces']))
          wdie.addstr(6, 1,"JOBS {0:04d}".format(dd['jobs']))
          temp_row = 8
          wdie.addstr(10,1,"VM   {0:.02f}".format(di.vm))
        else:
          wdie.addstr(2, 1,"VM   {0:.02f}".format(di.vm))
         #wdie.addstr(9, 1,"SQ    {0:02d}%".format(int(di.throttle)))
          temp_row = 4
          wdie.addstr(6, 1,"ACT    {0:02d}".format(di.active))
          wdie.addstr(7, 1,"PEND   {0:02d}".format(di.pending))
          wdie.addstr(8 ,1,"LHW  {0:04d}".format(dd['lhw']))
          wdie.addstr(9 ,1,"DHW  {0:04d}".format(dd['dhw']))
          wdie.addstr(10,1,"NNC  {0:04d}".format(dd['nonces']))
          wdie.addstr(11, 1,"JOBS {0:04d}".format(len(dd['work'])))
        if di.thermal_cutoff:
          wdie.addstr(temp_row, 4, "THM".format(temp), curses.color_pair(1))
        else:
          wdie.addstr(temp_row, 4, "{0:03d}".format(temp), color)


  def run_update(self):
    while 1:
      try:
        time.sleep(0.1)
        self.update()
      except:
        self.log("error during auto update")

  def update(self):
    try:
      # save cursor
      cy,cx = curses.getsyx()
      try:
        self.update_log()
        # run updates
        self.update_ui()
      except Exception as ex:
        self.log(str(ex))
      except:
        self.log("Unexpected Error")
      finally:
        self.refresh()
        # return cursor
        curses.setsyx(cy,cx)
        self.winput.refresh()
    except:
      self.log('error during update')

  def set_temperature(self, temperature):
    self.temperature = temperature

  def set_current(self, data):
    self.current = data

  def refresh(self):
    try:
      self.screen.refresh()
      self.wlog.refresh()
      self.wlogo.refresh()
      self.winfo.refresh()
      # module
      self.wmodule.refresh()
      # asic
      for wasic in self.wasic:
        if wasic is not None:
          wasic.refresh()
      # die
      for wdie in self.wdie:
        if wdie is not None:
          wdie.refresh()
      # expanded die
      for wexpdie in self.wexpdie:
        if wexpdie is not None:
          wexpdie.refresh()
      self.winput.refresh()
      self.woutput.refresh()
      if self.wprevious is not None:
        self.wprevious.refresh()
      if self.wstats is not None:
        self.wstats.refresh()
      self.refresh_ui()
    except:
      self.ui('error during refresh')

  def input(self, msg, color=6):
    while True:
      try:
        self.winput.erase()
        self.winput.bkgd(' ',curses.color_pair(color))
        self.winput.box()
        self.winput.addstr(0, 0, "INPUT")
        self.winput.addstr(1, 2, msg)
        self.winput.addstr(2, 2, "$")
        #self.refresh()
        ret = self.winput.getstr(2, 4).decode(encoding="utf-8")
        return ret
      except KeyboardInterrupt:
        self.log("exiting")
        self.end()
        raise
        break
      except:
        self.log("input error")

  def input_single(self, msg, color=6):
    while True:
      try:
        self.winput.erase()
        self.winput.bkgd(' ',curses.color_pair(color))
        self.winput.box()
        self.winput.addstr(0, 0, "INPUT")
        self.winput.addstr(1, 2, msg)
        self.winput.addstr(2, 2, "$")
        #self.refresh()
        ret = self.winput.getkey(2, 4)#.decode(encoding="utf-8")
        return ret
      except KeyboardInterrupt:
        self.log("exiting")
        self.end()
        raise
        break
      except:
        self.log("input error")

  def prompt_show(self, msg, color=0):
    self.winput.erase()
    self.winput.bkgd(' ',curses.color_pair(color))
    self.winput.box()
    self.winput.addstr(0, 0, "INPUT")
    self.winput.addstr(1, 2, msg)
    self.winput.addstr(2, 2, "$")
    #self.refresh()

  def prompt(self, msg, args):
    while True:
      ret = self.input(msg)
      if ret in args:
        return ret
      if ret == 'q':
        self.end()
        break

  def prompt_yn(self, msg):
    ret = self.prompt(msg + " [y/n]", 'yn')
    if ret == 'y':
      return True
    else:
      return False

  def prompt_int(self, msg):
    while True:
      ret = self.input(msg)
      try:
        ret_int = int(ret)
        return ret_int
      except ValueError:
        self.end()
        break

  def prompt_int_single(self, msg):
    while True:
      ret = self.input_single(msg)
      try:
        ret_int = int(ret)
        return ret_int
      except ValueError:
        self.end()
        break

  def prompt_enter(self, msg):
    ret = self.input(msg + " [Enter Continues]")
    if ret == 'q':
      self.end()

  def log(self, msg):
    self.log_buffer.append(msg)

  def end(self):
    curses.endwin()
    sys.exit(0)
