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

from .frame import HF_Frame, opcodes, opnames
from .frame import lebytes_to_int, int_to_lebytes


# Modeled on struct hf_usb_notice_data in hf_protocol.h.
class HF_OP_USB_NOTICE(HF_Frame):
  def __init__(self, initial_state):
    HF_Frame.__init__(self, initial_state)
    self.notification_code = self.hdata
    self.extra_data = None
    self.message = None
    if self.data_length_field > 0:
      self.extra_data = lebytes_to_int(self.data[0:4])
    if self.data_length_field > 1:
      try:
        raw_message = self.data[4:]
        first_NUL = raw_message.index(0)
      except ValueError:
        # Fix: Check that the last bytes are all NUL, there may be more than
        #      one, once the firmware is fixed to do that.
        raise HF_Error("OP_USB_NOTICE returned a non-NUL terminated string.")
      self.message = "".join([chr(x) for x in raw_message[0:first_NUL]])