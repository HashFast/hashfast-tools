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

from .frame import HF_Frame, hf_frame_data, opcodes, opnames
from .frame import lebytes_to_int, int_to_lebytes

class HF_OP_POWER(HF_Frame):
  def __init__(self, bytes=None, power=0x1):
    if bytes is None:
      # REQUEST
      HF_Frame.__init__(self,{'operation_code':   opcodes['OP_POWER'],
                              'chip_address':     0xFF,
                              'core_address':     0x00,
                              'hdata':            power }) # 0x1 diagnostic_power_on, 0x2 diagnostic_power_off
      self.construct_framebytes()
    else:
      # READ
      HF_Frame.__init__(self, bytes)

  def __str__(self):
    string  = "HF_OP_POWER\n"
    string += HF_Frame.__str__(self)
    return string