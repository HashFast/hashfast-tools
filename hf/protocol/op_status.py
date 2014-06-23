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

# Adapted from hf_protocol.h.
# Conversions for the ADC readings from GN on-chip sensors
def GN_CORE_VOLTAGE(a):
  assert a >= 0 and a < 2**8
  return (float(a)/float(256))*1.2

def GN_DIE_TEMPERATURE(a):
  assert a >= 0 and a < 2**16
  return (float(a)*float(240))/4096.0 - 61.5

# Imitates "struct hf_g1_monitor" in hf_protocols.h.
class hf_g1_monitor():
  def __init__(self, monitor_bytes):
    raw_temp = lebytes_to_int(monitor_bytes[0:2])
    self.die_temperature = GN_DIE_TEMPERATURE(raw_temp)
    self.core_voltage_main = GN_CORE_VOLTAGE(monitor_bytes[2])
    self.core_voltage_A = GN_CORE_VOLTAGE(monitor_bytes[3])
    self.core_voltage_B = GN_CORE_VOLTAGE(monitor_bytes[4])
    self.core_voltage_C = GN_CORE_VOLTAGE(monitor_bytes[5])
    self.core_voltage_D = GN_CORE_VOLTAGE(monitor_bytes[6])
    self.core_voltage_E = GN_CORE_VOLTAGE(monitor_bytes[7])

# Fix: Support all fields.
# Fix: Error check.
# Fix: Not sure how to handle this.  The monitoring values are
#      interpreted differently depending on what OP_CONFIG told the
#      die to do.  This information is not in the OP_STATUS packet.
#      For the moment we assume the "tachometer option" is not
#      used.  See page 33 of the GN Protocol Guide.  Guess we need
#      to support both interpretations and let the caller decide
#      which one is in effect.
# Fix: Figure out why most of the voltages are not present in OP_STATUS.
#      Perhaps I have to send out my own OP_CONFIG?
# Fix: We would like to decode the core map here, but this object does
#      not actually know how many cores there are.
class HF_OP_STATUS(HF_Frame):
  def __init__(self, initial_state):
    HF_Frame.__init__(self, initial_state)
    self.thermal_cutoff = (self.core_address & 0x80) >> 7
    self.tach_csec = self.core_address & 0x0f
    self.last_sequence_number = self.hdata
    self.monitor_data = hf_g1_monitor(self.data[0:16])
    self.coremap = self.data[8:]