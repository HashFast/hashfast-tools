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

from usb.core import USBError

from ..hf import HF_Error, HF_Thermal
from ..hf import Send, Receive
from ..hf import HF_Parse, Garbage
from ..hf import SHUTDOWN
from ..hf import decode_op_status_job_map, list_available_cores, rand_job, det_job
from ..hf import prepare_hf_hash_serial, check_nonce_work, sequence_a_leq_b

from ...protocol.frame            import HF_Frame, opcodes, opnames, lebytes_to_int
from ...protocol.op_settings      import HF_OP_SETTINGS, hf_settings, hf_die_settings
from ...protocol.op_power         import HF_OP_POWER
from ...protocol.op_usb_init      import HF_OP_USB_INIT
from ...protocol.op_usb_shutdown  import HF_OP_USB_SHUTDOWN
from ...protocol.op_hash          import HF_OP_HASH
from ...protocol.op_nonce         import HF_OP_NONCE
from ...protocol.op_status        import HF_OP_STATUS
from ...protocol.op_usb_notice    import HF_OP_USB_NOTICE
from ...protocol.op_fan           import HF_OP_FAN

from .base import BaseRoutine

class SettingsRoutine(BaseRoutine):

  def initialize(self):
    self.global_state = 'setup'
    self.op_settings = HF_OP_SETTINGS.forValues(settings=hf_settings())

  def setup(self, die, freq, volt):
    assert die < 4
    self.op_settings.settings.die[die] = hf_die_settings.forValues(frequency=freq, voltage=volt)
    self.op_settings.settings.generate_frame_data()
    self.op_settings.construct_framebytes()
    self.global_state = 'setup'

  def one_cycle(self):
    try:
      # Fix: Every time we send, we want also to receive (to make sure nothing
      #      deadlocks), so the send and receive objects should be combined.
      # Fix: Do we want to have a delay in here or some sort of select() like thing?
      self.receiver.receive()
      self.transmitter.send([])

      traffic = self.receiver.read()
      if traffic:
        self.parser.input(traffic)

      ####################
      # READ
      ####################
      if self.global_state is 'read':
        token = self.parser.next_token()
        if token:
          if isinstance(token, HF_OP_SETTINGS):
            self.process_op_settings(token)
            self.op_settings = token
            self.global_state = 'wait'
            return False
        op = HF_OP_SETTINGS()
        self.transmitter.send(op.framebytes)
        self.printer("Sent OP_SETTINGS request")

      ####################
      # WAIT
      ####################
      elif self.global_state is 'wait':
        time.sleep(1)

      ####################
      # SETUP
      ####################
      elif self.global_state is 'setup':
        self.op_settings.settings.generate_frame_data()
        self.op_settings.construct_framebytes()
        self.transmitter.send(self.op_settings.framebytes)
        self.printer("Sent OP_SETTINGS write")
        #self.printer(self.op_settings.framebytes)
        self.printer(self.op_settings)
        self.global_state = 'confirm'

      ####################
      # CONFIRM
      ####################
      elif self.global_state is 'confirm':
        token = self.parser.next_token()
        if token:
          if isinstance(token, HF_OP_SETTINGS):
            self.process_op_settings(token)
            time.sleep(1)
            op_power = HF_OP_POWER(power=0x1)
            self.transmitter.send(op_power.framebytes)
            self.printer("Sent OP_POWER")
            time.sleep(1)
            op_power = HF_OP_POWER(power=0x2)
            self.transmitter.send(op_power.framebytes)
            self.printer("Sent OP_POWER")
            time.sleep(1)
            self.global_state = 'bleh'
            return False
        op = HF_OP_SETTINGS()
        self.transmitter.send(op.framebytes)
        self.printer("Sent OP_SETTINGS request")

      else:
        # Unknown state
        raise HF_Error("Unknown global_state: %s" % (self.global_state))
      return True

    except KeyboardInterrupt:
      self.end()
      return False

    except USBError as e:
      #e.errno
      self.printer("USB Error: (%s, %s, %s)" % (sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
      self.end()
      return False

    except:
      self.printer("Generic exception handler: (%s, %s, %s)" % (sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
      self.end()
      return False