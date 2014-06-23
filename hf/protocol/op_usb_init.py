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

###
# Coremap
###

def dice_up_coremap(lebytes, dies, cores):
  assert len(lebytes) % 4 == 0
  assert 8 * len(lebytes) >= dies * cores
  assert dies > 0 and cores > 0
  die_modulus = 2 ** cores
  global_bitmap = lebytes_to_int(lebytes)
  die_coremaps = []
  for die in range(dies):
    single_die_map = coremap_array(global_bitmap % die_modulus, cores)
    die_coremaps = [single_die_map] + die_coremaps
    global_bitmap = global_bitmap >> cores
  return die_coremaps

def coremap_array(die_bitmap, cores):
  result = []
  mask = 0x1
  for i in range(cores):
    if die_bitmap & mask > 0:
      result = result + [1]
    else:
      result = result + [0]
    mask = mask << 1
  return result

def display_cores_by_G1_location(ca, printer):
  for line in display_cores_by_G1_location_lines(ca):
    printer(line)

def display_cores_by_G1_location_lines(ca):
  def I(yesno):
    if yesno > 0:
      return 'x'
    else:
      return ' '
  def NI(yesno):
    if yesno > 0:
      return 'X'
    else:
      return ' '
  assert len(ca) == 96
  return ["".join([NI(ca[95]),  I(ca[74]), NI(ca[73]),  I(ca[53]), NI(ca[52]),  I(ca[33]), NI(ca[32]),  I(ca[11]), NI(ca[10])]),
      "".join([ I(ca[94]), NI(ca[75]),  I(ca[72]), NI(ca[54]),  I(ca[51]), NI(ca[34]),  I(ca[31]), NI(ca[12]),  I(ca[9])]),
      "".join([NI(ca[93]),  I(ca[76]), NI(ca[71]),  I(ca[55]), NI(ca[50]),  I(ca[35]), NI(ca[30]),  I(ca[13]), NI(ca[8])]),
      "".join([ I(ca[92]), NI(ca[77]),  I(ca[70]), NI(ca[56]),  I(ca[49]), NI(ca[36]),  I(ca[29]), NI(ca[14]),  I(ca[7])]),
      "".join([NI(ca[91]),  I(ca[78]), NI(ca[69]),  I(ca[57]), NI(ca[48]),  I(ca[37]), NI(ca[28]),  I(ca[15]), NI(ca[6])]),
      "".join([ I(ca[90]), NI(ca[79]),  I(ca[68]), NI(ca[58]),  I(ca[47]), NI(ca[38]),  I(ca[27]), NI(ca[16]),  I(ca[5])]),
      "".join([NI(ca[89]),  I(ca[80]), NI(ca[67]),  I(ca[59]), NI(ca[46]),  I(ca[39]), NI(ca[26]),  I(ca[17]), NI(ca[4])]),
      "".join([ I(ca[88]), NI(ca[81]),  I(ca[66]), NI(ca[60]),  I(ca[45]), NI(ca[40]),  I(ca[25]), NI(ca[18]),  I(ca[3])]),
      "".join([NI(ca[87]),  I(ca[82]), NI(ca[65]),  I(ca[61]), NI(ca[44]),  I(ca[41]), NI(ca[24]),  I(ca[19]), NI(ca[2])]),
      "".join([ I(ca[86]), NI(ca[83]),  I(ca[64]), NI(ca[62]),  I(ca[43]), NI(ca[42]),  I(ca[23]), NI(ca[20]),  I(ca[1])]),
      "".join([NI(ca[85]),  I(ca[84]), NI(ca[63]),      'O',          'O',        'O', NI(ca[22]),  I(ca[21]), NI(ca[0])])]

# Fix: This really needs test code and documentation.  Make sure it
#      works for future designs as well as G1.
def decode_op_status_job_map(jobmap, cores):
  assert 8 * len(jobmap) <= 2 * cores
  bitmap = lebytes_to_int(jobmap)
  active_map = [0] * cores
  for i in range(cores):
    if bitmap & (1 << 2*i) > 0:
      active_map[i] = 1
  pending_map = [0] * cores
  for i in range(cores):
    if bitmap & (1 << (2*i + 1)) > 0:
      pending_map[i] = 1
  return [active_map, pending_map]

# Fix: Remove this if we don't need it.
# Find empties: takes core list like [0,1,0,0,1...] and converts to
# dictionary in which each key is an empty slot.
def core_list_to_dict(corelist):
  empties = {}
  for i in range(len(corelist)):
    if corelist[i] == 0:
      empties[i] = 1
  return empties

# Fix: cores -> slots
def list_available_cores(corelist):
  empties = []
  for i in range(len(corelist)):
    if corelist[i] == 0:
      empties.append(i)
  return empties