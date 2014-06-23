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

class hf_die_settings(hf_frame_data):
  LENGTH = 4

  @classmethod
  def forValues(cls, frequency=550, voltage=0):
    obj = cls()
    obj.frequency           = frequency
    obj.voltage             = voltage
    obj.generate_frame_data()
    return obj

  def initialize(self):
    self.frequency  = 550
    self.voltage    = 0

  def parse_frame_data(self, bytes):
    assert len(bytes) >= self.LENGTH
    self.frame_data         = bytes
    self.frequency          = lebytes_to_int(bytes[0:2]) # MHz
    self.voltage            = lebytes_to_int(bytes[2:4]) # mV, 0 = die not enabled. (Rev-1 kludge right now - If b15 set = dac_setting)

  def generate_frame_data(self):
    self.frame_data         = int_to_lebytes(self.frequency, 2)
    self.frame_data        += int_to_lebytes(self.voltage, 2)
    return self.frame_data

  def __str__(self):
    if self.voltage & 0x8000:
      string  = "Frequency: {0} MHz   Voltage: {1} d".format(self.frequency, self.voltage & 0x7FFF)
    else:
      string  = "Frequency: {0} MHz   Voltage: {1} mV".format(self.frequency, self.voltage)
    return string

class hf_settings(hf_frame_data):
  LENGTH = 20
  MAGIC  = 0x42AA

  @classmethod
  def forValues(cls, revision=1, ref_frequency=25, die=None):
    obj = cls()
    obj.revision            = revision
    obj.ref_frequency       = ref_frequency
    if die is None:
      obj.die                = [hf_die_settings()]*4
    else:
      obj.die                 = die
    obj.generate_frame_data()
    return obj

  def initialize(self):
    self.revision       = 1
    self.ref_frequency  = 25
    self.die            = [hf_die_settings()]*4


  def parse_frame_data(self, bytes):
    assert len(bytes) >= self.LENGTH
    self.frame_data         = bytes
    self.revision           = bytes[0]                      # revision number
    self.ref_frequency      = bytes[1]                      # reference clock
    self.magic              = lebytes_to_int(bytes[2:4])    # extra validation
    self.die                = [hf_die_settings()]*4
    for x in range(4):
      size                  = x*hf_die_settings.LENGTH
      self.die[x]           = hf_die_settings(bytes[(4+size):(8+size)])

  def generate_frame_data(self):
    self.frame_data         = [self.revision]
    self.frame_data        += [self.ref_frequency]
    self.frame_data        += int_to_lebytes(self.MAGIC, 2)
    for x in range(4):
      self.frame_data      += self.die[x].generate_frame_data()
    return self.frame_data

  def __str__(self):
    string  = "HF Settings\n"
    string += "Revision             {0}\n".format(self.revision)
    string += "Reference Clock      {0} MHz\n".format(self.ref_frequency)
    for x in range(4):
      string += "Die {0}:     {1}\n".format(x, self.die[x])
    return string

class HF_OP_SETTINGS(HF_Frame):
  def __init__(self, bytes=None):
    if bytes is None:
      # REQUEST
      HF_Frame.__init__(self,{'operation_code':   opcodes['OP_SETTINGS'],
                              'chip_address':     0x00,
                              'core_address':     0x00,     # write disable
                              'hdata':            0x42AA})
      self.construct_framebytes()
    else:
      # READ
      HF_Frame.__init__(self, bytes)
      self.settings = hf_settings(self.data[0:20])

  @classmethod
  def forValues(cls, settings=None):
    assert isinstance(settings, hf_settings)
    obj = cls()
    obj.settings = settings
    obj.core_address = 0x01 # write enable
    obj.construct_framebytes()
    return obj

  def construct_framebytes(self):
    if hasattr(self, 'settings'):
      self.set_data(self.settings.generate_frame_data())
    HF_Frame.construct_framebytes(self)

  def __str__(self):
    string  = "HF_OP_SETTINGS\n"
    string += "operation_code:      {:#x}\n".format(self.operation_code)
    string += "chip_address:        {:#x}\n".format(self.chip_address)
    string += "Write Enable:        {:#x}\n".format(self.core_address)
    string += "hdata:               {:#x}\n".format(self.hdata)
    string += "data_length_field:   {}\n".format(self.data_length)
    if hasattr(self, 'settings'):
      string += "{0}".format(self.settings)
    return string