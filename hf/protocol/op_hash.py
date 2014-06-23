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

# Imitates "struct hf_hash_serial" in hf_protocols.h.
class hf_hash_serial():
    def __init__(self, midstate, merkle_residual, timestamp, bits, starting_nonce,
                 nonce_loops, ntime_loops, search_difficulty, option, group, spare3):
        assert len(midstate) == 32
        assert {x >= 0 and x < 256 for x in midstate} == set([True])
        assert len(merkle_residual) == 4
        assert {x >= 0 and x < 256 for x in merkle_residual} == set([True])
        assert timestamp >= 0 and timestamp < 2**32
        assert bits >= 0 and bits < 2**32
        assert starting_nonce >= 0 and starting_nonce < 2**32
        assert nonce_loops >= 0 and nonce_loops < 2**32
        assert ntime_loops >= 0 and ntime_loops < 2**16
        assert search_difficulty >= 0 and search_difficulty < 256
        assert option >= 0 and option < 256
        assert group >= 0 and option < 256
        assert len(spare3) == 3
        assert {x >= 0 and x < 256 for x in spare3} == set([True])

        self.midstate = midstate
        self.merkle_residual = merkle_residual
        self.timestamp = timestamp
        self.bits = bits
        self.starting_nonce = starting_nonce
        self.nonce_loops = nonce_loops
        self.ntime_loops = ntime_loops
        self.search_difficulty = search_difficulty
        self.option = option
        self.group = group
        self.spare3 = spare3
        self.generate_frame_data()

    def generate_frame_data(self):
        self.frame_data = self.midstate + self.merkle_residual + \
            int_to_lebytes(self.timestamp, 4) + int_to_lebytes(self.bits, 4) + \
            int_to_lebytes(self.starting_nonce, 4) + int_to_lebytes(self.nonce_loops, 4) + \
            int_to_lebytes(self.ntime_loops, 2) + [self.search_difficulty] + \
            [self.option] + [self.group] + self.spare3

# Fix: We would like to confirm that chip_address and core_address make sense
#      for our particular hardware, but that information is not available
#      to this object.
class HF_OP_HASH(HF_Frame):
  def __init__(self, chip_address, core_address, sequence, job):
    assert chip_address >= 0 and chip_address < 256
    assert core_address >= 0 and core_address < 256
    assert sequence >= 0 and sequence < 2**16
    assert isinstance(job, hf_hash_serial)
    self.job = job
    HF_Frame.__init__(self,{'operation_code': opcodes['OP_HASH'],
                            'chip_address': chip_address,
                            'core_address': core_address,
                            'hdata': sequence,
                            'data': self.job.frame_data})