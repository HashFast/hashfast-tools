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

import random
import sys
import time

from abc import ABCMeta, abstractmethod

from collections import deque

from ..hf import Send, Receive
from ..hf import HF_Parse, Garbage
from ..hf import SHUTDOWN
from ..hf import rand_job, det_job, known_job
from ..hf import check_nonce_work, sequence_a_leq_b, prepare_hf_hash_serial

from ...errors                    import HF_Error, HF_Thermal, HF_InternalError, HF_NotConnectedError
from ...util                      import with_metaclass, int_to_lebytes, lebytes_to_int, reverse_every_four_bytes
from ...protocol.frame            import HF_Frame, opcodes, opnames
from ...protocol.op_settings      import HF_OP_SETTINGS, hf_settings, hf_die_settings
from ...protocol.op_power         import HF_OP_POWER
from ...protocol.op_usb_init      import HF_OP_USB_INIT, decode_op_status_job_map, list_available_cores
from ...protocol.op_usb_shutdown  import HF_OP_USB_SHUTDOWN
from ...protocol.op_hash          import HF_OP_HASH
from ...protocol.op_nonce         import HF_OP_NONCE
from ...protocol.op_status        import HF_OP_STATUS
from ...protocol.op_usb_notice    import HF_OP_USB_NOTICE
from ...protocol.op_fan           import HF_OP_FAN

# Fix: Turning this into a callable module:
#      Need to provide a print function or None for no output.
#      Need a "do something" function so calling code can retain control.
#        Needs a return value for errors or stopping.
#      Does Python have a destroy method for class instances?
#      Probably need a run-for-this-long -- either hashes or time -- feature.
#        Which probably wants a function which just runs until it's done.
#      Ultimately: can probably fully decompose the problem into a number
#      of hierarchical classes.  Pass in objects or functions for USB operation
#      and anything else that requires customization.  This allows good test
#      code.

def noprint(x):
  pass

class BaseRoutine(with_metaclass(ABCMeta, object)):
  def __init__(self, talkusb, clockrate, printer=noprint, deterministic=False):
    self.talkusb = talkusb
    self.clockrate = clockrate
    self.printer = printer
    self.deterministic = deterministic

    # call defults
    self.defaults()

    # call user initialize
    self.initialize()

  def defaults(self):
    self.max_die = 4*5
    self.max_cores_per_die = 96

    self.cores_per_die = 0
    self.number_of_die = 0

    self.op_usb_init_delay = 12
    self.last_op_usb_init_sent = 0

    # test stats, hash rate stats, search difficulty, default unknown global state
    self.test_start = None
    self.hash_rate_start = None
    self.moving_interval = 8
    self.search_difficulty = 32
    self.global_state = 'unknown'

    # random
    self.random_source = "/dev/urandom"
    self.rndsrc = open(self.random_source, 'rb')
    random.seed(self.rndsrc.read(256))

    # parser, transmitter, receiver
    self.parser = HF_Parse()
    self.transmitter = Send(self.talkusb)
    self.receiver = Receive(self.talkusb)

    # setup stats
    self.stats = {'hashes':0, 'hashrate':0, 'nonces':0, 'lhw':0, 'dhw':0, 'chw':0}

    # setup die stats
    self.dies = [{'die':i, 'sequence':0, 'work':{}, 'hashes':0, 'jobs':0, 'hashrate':0.0, 'nonces':0, 'lhw':0, 'dhw':0, 'chw':0,
                  'pending_slots':{}, 'active_slots':{}, 'core_sequence':{}, 'last_sequence':None, 'active':0, 'pending':0, 'moving':None,
                  'thermal_cutoff':0, 'frequency':0, 'voltage':0, 'temperature':0, 'core_voltage':0, 'vin':0, 'vout':0, 'elapsed':0}
                  for i in range(self.max_die)]

    # setup core stats
    self.cores= [{'core':i,'sequence':0, 'work':{}, 'hashes':0, 'hashrate':0, 'nonces':0, 'lhw':0, 'dhw':0} 
                  for i in range(self.max_die*self.max_cores_per_die)]
    for core in self.cores:
      core['work'] = deque([])    

  @abstractmethod
  def initialize(self):
    pass

  def get_die(self, idie):
    return self.dies[idie]

  def get_core(self, idie, icore):
    # Fix: use dynamic numbers
    return self.cores[idie*96 + icore]

  def calculate_hashrate(self):
    if self.test_start is not None:
      elapsed = time.time() - self.test_start
      self.stats['hashrate'] = self.stats['hashes'] / elapsed
      for this_die in self.dies:
        this_die['hashrate'] = this_die['hashes']   / elapsed
        this_die['elapsed']  = elapsed
        # compute moving hashrate
        if this_die['moving'] is None:
          # first moving hashrate
          moving =   {'elapsed':elapsed, 'hashes':this_die['hashes'], 'nonces':0,    'lhw':0,     'dhw':0,
                                         'hashrate':0,                'noncerate':0, 'lhwrate':99999, 'dhwrate':99999 }
          this_die['moving'] = [ moving ]
        else:
          # last recorded moving hashrate
          last_moving = this_die['moving'][-1]
          moving_elapsed = elapsed - last_moving['elapsed']
          # only compute every moving_interval
          if moving_elapsed > self.moving_interval:
            moving = {'elapsed':elapsed, 'hashes':this_die['hashes'], 'nonces':this_die['nonces'], 'lhw':this_die['lhw'], 'dhw':this_die['dhw'],
                                         'hashrate':0,                'noncerate':0,               'lhwrate':0,           'dhwrate':0 }
            moving_hashes       = moving['hashes'] - last_moving['hashes']
            moving['hashrate']  = moving_hashes / moving_elapsed
            moving['noncerate'] = moving['nonces'] - last_moving['nonces']
            moving['lhwrate']   = moving['lhw']    - last_moving['lhw']
            moving['dhwrate']   = moving['dhw']    - last_moving['dhw']
            this_die['moving'].append(moving)
      return True
    else:
      return False


  def get_hashrate(self):
    self.calculate_hashrate()
    return self.stats['hashrate']

  def report_hashrate(self):
    if self.calculate_hashrate():
      self.printer(  "avg hashrate: {0:6.2f} GH/s, nonces {1:d}".format((self.stats['hashrate']/10**9), self.stats['nonces']))
      for this_die in self.dies:
        self.printer("Die {2:d}, avg hashrate: {0:6.2f} GH/s, nonces: {1:d}, {3}sec moving {4:6.2f} GH/s"
          .format((this_die['hashrate']/10**9), this_die['nonces'], this_die['die'], self.moving_interval, (this_die['moving'][-1]['hashrate']/10**9)))

  def report_errors(self):
    self.printer(  "Errors:    LHW: {0:d}   DHW: {1:d}   CHW: {2:d}".format(self.stats['lhw'], self.stats['dhw'], self.stats['chw']))
    for this_die in self.dies:
      self.printer("Die {3:d}, LHW: {0:d}   DHW: {1:d}   CHW: {2:d}  T: {4:f} V: {5:f}".format(this_die['lhw'], this_die['dhw'], this_die['chw'], this_die['die'], this_die['temperature'], this_die['core_voltage']))

  def process_op_usb_init(self, op_usb_init):
    # parse OP_USB_INIT
    self.number_of_die = op_usb_init.dies_present
    assert self.max_die >= self.number_of_die
    self.cores_per_die = op_usb_init.cores_per_die
    assert self.max_cores_per_die >= self.cores_per_die
    # remove unused die
    self.dies = self.dies[:self.number_of_die]
    # print OP_USB_INIT
    self.printer(str(op_usb_init))
    # check operation status
    if op_usb_init.init_base.operation_status != 0:
      raise HF_Error("operation_status not successful: %d" % (op_usb_init.init_base.operation_status))
    if self.test_start is None:
      self.test_start = time.time()

  def is_valid_nonce(self, this_job, nonce):
    # check nonce
    if self.deterministic:
      return (nonce in this_job['solutions'])
    else:
      zerobits, regen_hash_expanded = check_nonce_work(this_job, nonce)
      #self.printer(this_job)
      #self.printer('req: ' + ''.join('{:02x}'.format(x) for x in int_to_lebytes(3184732951, 4)))
      #self.printer('got: ' + ''.join('{:02x}'.format(x) for x in int_to_lebytes(nonce, 4)))
      #self.printer(zerobits)
      #self.printer(regen_hash_expanded)
      return (zerobits >= self.search_difficulty)

  def process_op_nonce(self, op_nonce):
    # calculate hashrate here
    self.calculate_hashrate()
    # continue with op_nonce
    for nonce in op_nonce.nonces:
      die = op_nonce.chip_address
      this_die = self.get_die(die)
      if nonce.sequence in this_die['work']:
        # sequence number found
        this_work = this_die['work'][nonce.sequence]
        this_job  = this_work['job']
        # core
        core = this_work['core']
        this_core = self.get_core(die, core)
        # check nonce
        if self.is_valid_nonce(this_job, nonce.nonce):
          # start timing hashrate
          if self.hash_rate_start is None:
            self.hash_rate_start = time.time()
          # hashes
          self.stats['hashes']  += 2**self.search_difficulty
          this_die['hashes']    += 2**self.search_difficulty
          # nonces
          self.stats['nonces']  += 1
          this_die['nonces']    += 1
          this_core['nonces']   += 1
          # receieved
          this_work['recieved'] += 1
          #self.printer("GOOD NNC (%08x) die: %d core: %d seq: %d" % (nonce.nonce, die, core, nonce.sequence))

        else:
          # difficulty too low
          self.stats['lhw']     += 1
          this_die['lhw']       += 1
          this_core['lhw']      += 1
          #self.printer("!BAD NNC (%08x) die: %d core: %d seq: %d" % (nonce.nonce, die, core, nonce.sequence))

      else:
        # sequence number corrupted
        self.stats['chw']       += 1
        this_die['chw']         += 1
        #self.printer("  CRPT SEQ (%08x) die: %d seq: %d" % (nonce.nonce, die, nonce.sequence))

  def process_op_status(self, op_status):
    die = op_status.chip_address
    this_die = self.get_die(die)
    # check thermal
    if op_status.thermal_cutoff:
      this_die['thermal_cutoff'] = op_status.thermal_cutoff
      raise HF_Thermal("THERMAL CUTOFF, die %d" % (die))
    # last sequence seen
    this_die['last_sequence'] = op_status.last_sequence_number
    # active / pending core map
    active, pending  = decode_op_status_job_map(op_status.coremap, self.cores_per_die)
    this_die['active']  = len([core for core in active  if core is 1])
    this_die['pending'] = len([core for core in pending if core is 1])
    # raw core list
    raw_pending_slots = list_available_cores(pending)
    raw_active_slots  = list_available_cores(active)
    pending_slots = \
      [core for core in raw_pending_slots \
         if core not in this_die['core_sequence'] \
         or sequence_a_leq_b(this_die['core_sequence'][core], op_status.last_sequence_number)]
    active_slots = \
      [core for core in raw_active_slots \
         if core not in this_die['core_sequence'] \
         or sequence_a_leq_b(this_die['core_sequence'][core], op_status.last_sequence_number)]
    # shuffle the slot list
    random.shuffle(pending_slots)
    random.shuffle(active_slots)
    this_die['pending_slots'] = pending_slots
    this_die['active_slots']  = active_slots
    # die measured temperature and voltage
    this_die['temperature']   = op_status.monitor_data.die_temperature
    this_die['core_voltage']  = op_status.monitor_data.core_voltage_main
    # op_status message
    if this_die['active'] is not 96:
      self.printer("OP_STATUS die: %d active: %s pending: %s" % (die, this_die['active'], this_die['pending']))

  def process_op_settings(self, op_settings):
    self.printer("Got OP_SETTINGS")
    self.printer(str(op_settings))
    for x in range(4): #op_settings.settings.die:
      self.dies[x]['frequency'] = op_settings.settings.die[x].frequency
      self.dies[x]['voltage'] = op_settings.settings.die[x].voltage

  def get_job(self, die, core):
    this_die  = self.get_die(die)
    this_core = self.get_core(die, core)
    # current sequence
    sequence = this_die['sequence']
    # get job
    if self.deterministic:
      # get deterministic job
      job = det_job(sequence)
      return job
    else:
      # get random job
      job = rand_job(self.rndsrc)
      return job

  def action_op_hash(self, die, core):
    this_die  = self.get_die(die)
    this_core = self.get_core(die, core)
    # current sequence
    sequence = this_die['sequence']
    # get job
    job = self.get_job(die, core)
    # generate OP_HASH
    op_hash = HF_OP_HASH(die, core, sequence, prepare_hf_hash_serial(job, self.search_difficulty))
    # generate work
    work = {'time':time.time(), 'job':job, 'die':die, 'core':core, 'recieved':0}
    # send OP_HASH
    self.transmitter.send(op_hash.framebytes)
    # Fix: overwrites previous core_sequence
    this_die['core_sequence'][core] = sequence
    this_die['work'][sequence] = work
    this_die['jobs'] = len(this_die['work'])
    # new sequence
    this_die['sequence'] = (this_die['sequence'] + 1) % 2**16
    if self.deterministic:
      # dark error calculations
      this_core['work'].append(work)
      while (len(this_core['work']) > 2):
        done_work = this_core['work'].popleft()
        done_job  = done_work['job']
        ndhw = ( len(done_job['solutions']) - done_work['recieved'])
        self.stats['dhw'] += ndhw
        this_die['dhw']   += ndhw
        this_core['dhw']  += ndhw

  @abstractmethod
  def one_cycle(self):
    pass

  def n_cycles(self, n):
    for i in range(n):
      rslt = self.one_cycle()
      if rslt != True:
        return False
    return True

  def end(self):
    self.report_hashrate()
    op_usb_shutdown = HF_Frame({'operation_code': opcodes['OP_USB_SHUTDOWN'], 'hdata': 2})
    self.transmitter.send(op_usb_shutdown.framebytes)
    self.printer("Sent OP_USB_SHUTDOWN.")
    self.talkusb(SHUTDOWN, None, 0)
    return False

  def __del__(self):
    self.rndsrc.close()
