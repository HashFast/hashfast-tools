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

# From hf_protocol.h
HF_NTIME_MASK = 0x0fff       # Mask for for ntime
# If this bit is set, search forward for other nonce(s)
HF_NONCE_SEARCH = 0x1000     # Search bit in candidate_nonce -> ntime

# Imitates "strudct hf_candidate_nonce" in hf_protocols.h.
class hf_candidate_nonce:
  def __init__(self, nonce_bytes):
    assert len(nonce_bytes) == 8
    self.nonce = lebytes_to_int(nonce_bytes[0:4])
    self.sequence = lebytes_to_int(nonce_bytes[4:6])
    self.ntime = lebytes_to_int(nonce_bytes[6:8])
    self.ntime_offset = self.ntime & HF_NTIME_MASK
    self.search_forward = self.ntime & HF_NONCE_SEARCH

class HF_OP_NONCE(HF_Frame):
  def __init__(self, framebytes):
    HF_Frame.__init__(self, framebytes)
    assert len(self.data) % 8 == 0
    self.nonces = []
    for i in range(int(len(self.data) / 8)):
      self.nonces = self.nonces + [hf_candidate_nonce(self.data[8*i:8*i+8])]