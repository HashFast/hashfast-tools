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
from .op_config import hf_config_data

class hf_usb_init_base(hf_frame_data):
  LENGTH = 16

  def initialize(self):
    self.firmware_rev     = 0
    self.hardware_rev     = 0
    self.serial_number    = 0
    self.operation_status = 0
    self.extra_status     = [0]*3
    self.hash_clock_rate  = 0
    self.inflight_target  = 0
      
  def parse_frame_data(self, bytes):
    assert len(bytes) >= self.LENGTH
    self.firmware_rev     = lebytes_to_int(bytes[0:2])
    self.hardware_rev     = lebytes_to_int(bytes[2:4])
    self.serial_number    = lebytes_to_int(bytes[4:8])
    self.operation_status = bytes[8]
    for x in range(3):
      self.extra_status[x]= bytes[(9+x)]
    self.hash_clock_rate  = lebytes_to_int(bytes[12:14])
    self.inflight_target  = lebytes_to_int(bytes[14:16])

  def generate_frame_data(self):
    self.frame_data    = int_to_lebytes(self.firmware_rev, 2)
    self.frame_data   += int_to_lebytes(self.hardware_rev, 2)
    self.frame_data   += int_to_lebytes(self.serial_number, 4)
    self.frame_data   += [self.operation_status]
    for status in self.extra_status:
      self.frame_data += [status]
    self.frame_data   += int_to_lebytes(self.hash_clock_rate, 2)
    self.frame_data   += int_to_lebytes(self.inflight_target, 2)
    return self.frame_data

  def __str__(self):
    string    = "hf_usb_init_base\n"
    string   += "Firmware Rev.            {0}\n".format(self.firmware_rev)
    string   += "Hardware Rev.            {0}\n".format(self.hardware_rev)
    string   += "Serial Number            {0:#x}\n".format(self.serial_number)
    string   += "Operation Status         {0}\n".format(self.operation_status)
    for status in self.extra_status:
      string += "Extra Status             {0}\n".format(status)
    string   += "Hash Clockrate           {0} MHz\n".format(self.hash_clock_rate)
    string   += "Inflight Target          {0}\n".format(self.inflight_target)
    return string

# Fix: Support all fields.
# Fix: Error check.
class HF_OP_USB_INIT(HF_Frame):
  # host-device communication protocls
  PROTOCOL_USB_MAPPED_SERIAL = 0
  PROTOCOL_GLOBAL_WORK_QUEUE = 1

  def __init__(self, bytes=None, protocol=0, override=0, pll=0, asic=0, speed=0, shed=1, clockrate=550):
    if bytes is None:
      # core_address fields
      # bits 2:0: Protocol to use
      # bit  3:   Override configuration data
      # bit  4:   PLL bypass
      # bit  5:   Disable automatic ASIC initialization sequence
      # bit  6:   At speed core test, return bitmap separately.
      # bit  7:   Host supports gwq status shed_count
      # If the uc thinks shed_supported is off, then it automatically disables
      # core 95.  This only affects GWQ mode.  We turn it on so that core 95
      # shows up on the working core map.
      init_opt = protocol | (override << 3) | (pll << 4) | (asic << 5) | (speed << 6) | (shed << 7)
      HF_Frame.__init__(self,{'operation_code': opcodes['OP_USB_INIT'],
                              'core_address':   init_opt,
                              'hdata':          clockrate })
    else:
      HF_Frame.__init__(self, bytes)
      self.dies_present     = self.chip_address
      self.cores_per_die    = self.core_address
      self.device_id        = (self.hdata & 0xFF)
      self.reference_clock  = (self.hdata >> 8)
      self.init_base        = hf_usb_init_base(self.data[0:16])
      self.config           = hf_config_data(self.data[16:32])

  @classmethod
  def forValues(cls, protocol=0, pll=0, asic=0, speed=0, shed=1, clockrate=550, config=None):
    assert clockrate is not None
    if config is not None:
      assert isinstance(config, hf_config)
      override = 1
    else:
      override = 0
    # OP_USB_INIT
    obj = cls(protocol, override, pll, asic, speed, shed, clockrate)
    # self.config = config
    return obj

  def construct_framebytes(self):
    if hasattr(self, 'config'):
      self.set_data(self.config.generate_frame_data())
    HF_Frame.construct_framebytes(self)

  def __str__(self):
    string  = "OP_USB_INIT\n"
    string += "Dies Present             {0}\n".format(self.dies_present)
    string += "Cores per Die            {0}\n".format(self.cores_per_die)
    string += "Device ID                {0}\n".format(self.device_id)
    string += "Reference Clock          {0} MHz\n".format(self.reference_clock)
    if hasattr(self, 'init_base'):
      string += "{0}".format(self.init_base)
    if hasattr(self, 'config'):
      string += "{0}".format(self.config)
    return string