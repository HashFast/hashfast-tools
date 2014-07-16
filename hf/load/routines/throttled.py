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

from ..hf import Send, Receive
from ..hf import HF_Parse, Garbage
from ..hf import SHUTDOWN
from ..hf import rand_job, det_job
from ..hf import check_nonce_work, sequence_a_leq_b

from ...errors                    import HF_Error, HF_Thermal, HF_InternalError, HF_NotConnectedError
from ...util                      import with_metaclass, int_to_lebytes, lebytes_to_int
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

from .base import BaseRoutine

class ThrottledRoutine(BaseRoutine):

  def initialize(self):
    self.global_state = 'settings'

  def one_cycle(self, throttle):
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
      # SETTINGS
      ####################
      if self.global_state == 'settings':
        while self.parser.has_token():
          token = self.parser.next_token()
          if token:
            if isinstance(token, HF_OP_SETTINGS):
              self.process_op_settings(token)
              # state starting
              self.global_state = 'starting'
              return True
        op = HF_OP_SETTINGS()
        self.transmitter.send(op.framebytes)
        self.printer("Sent OP_SETTINGS request")
        time.sleep(0.1)
      
      ####################
      # STARTING
      ####################
      elif self.global_state == 'starting':
        # check for returned OP_USB_INIT
        while self.parser.has_token():
          token = self.parser.next_token()
          if token:
            if isinstance(token, HF_OP_USB_INIT):
              self.process_op_usb_init(token)
              # send OP_FAN
              op_fan = HF_OP_FAN(speed=99)
              self.transmitter.send(op_fan.framebytes)
              self.printer("Sent OP_FAN.")
              # state running
              self.global_state = 'running'
              return True
        if (time.time() - self.last_op_usb_init_sent) > self.op_usb_init_delay:
          # send OP_UST_INIT
          op_usb_init = HF_OP_USB_INIT(clockrate=self.clockrate)
          self.transmitter.send(op_usb_init.framebytes)
          self.printer("Sent OP_USB_INIT")
          self.last_op_usb_init_sent = time.time()

      ####################
      # RUNNING
      ####################
      elif self.global_state == 'running':
        # handle tokens
        while(self.parser.has_token()):
          token = self.parser.next_token()
          if token:
            if isinstance(token, HF_OP_NONCE):
              self.process_op_nonce(token)
            elif isinstance(token, HF_OP_STATUS):
              self.process_op_status(token)
            elif isinstance(token, HF_OP_USB_NOTICE):
              self.printer("OP_USB_NOTICE code: %d extra: %d message: %s" % (token.notification_code, token.extra_data, token.message))
            elif isinstance(token, HF_Frame):
              self.printer("Received HF_Frame() with %s operation." % (opnames[token.operation_code]))
            elif isinstance(token, Garbage):
              self.printer("Garbage: %d bytes" % (len(token.garbage)))
            else:
              raise HF_Error("Unexpected token type: %s" % (token))
        # first stock the active slots.
        for die in range(self.number_of_die):
          this_die = self.dies[die]
          receiver_throttle_counter = 0
          for i in range(throttle):
            if len(this_die['active_slots']) > 0:
              this_die['active_slots'].pop()
          for core in this_die['active_slots']:
            # send op_hash
            self.action_op_hash(die, core)
            # Fix: throttled reciever
            receiver_throttle_counter += 1
            if receiver_throttle_counter % 10 is 0:
              self.receiver.receive()
          this_die['active_slots'] = []
        # next stock the pending slots.
        if throttle < 1:
          for die in range(self.number_of_die):
            this_die = self.dies[die]
            receiver_throttle_counter = 0
            for core in this_die['pending_slots']:
              # send op_hash
              self.action_op_hash(die, core)
              # Fix: throttled reciever
              receiver_throttle_counter += 1
              if receiver_throttle_counter % 10 is 0:
                self.receiver.receive()
            this_die['pending_slots'] = []

      ####################
      # SHUTDOWN
      ####################
      elif self.global_state == 'shutdown':
        # handle tokens
        while(self.parser.has_token()):
          token = self.parser.next_token()
          if token:
            if isinstance(token, HF_OP_NONCE):
              self.process_op_nonce(token)
            elif isinstance(token, HF_OP_STATUS):
              self.process_op_status(token)
            elif isinstance(token, HF_OP_USB_NOTICE):
              self.printer("OP_USB_NOTICE code: %d extra: %d message: %s" % (token.notification_code, token.extra_data, token.message))
            elif isinstance(token, HF_Frame):
              self.printer("Received HF_Frame() with %s operation." % (opnames[token.operation_code]))
            elif isinstance(token, Garbage):
              self.printer("Garbage: %d bytes" % (len(token.garbage)))
            else:
              raise HF_Error("Unexpected token type: %s" % (token))
        # perform action
        for die in range(self.number_of_die):
          this_die = self.dies[die]
          if this_die['active']  is not 0:
            return True
          if this_die['pending'] is not 0:
            return True
        self.report_hashrate()
        return False

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

    except HF_Thermal:
      self.printer("Generic exception handler: (%s, %s, %s)" % (sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
      self.end()
      return False

    except:
      self.printer("Generic exception handler: (%s, %s, %s)" % (sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
      self.end()
      return False