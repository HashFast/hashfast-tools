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

from abc import ABCMeta, abstractmethod

from ..load import crc
from ..util import with_metaclass, int_to_lebytes, lebytes_to_int

# Operation codes from hf_protocol.h.
opcodes = {
  # Serial protocol operation codes (Second header byte)
  'OP_NULL':              0,
  'OP_ROOT':              1,
  'OP_RESET':             2,
  'OP_PLL_CONFIG':        3,
  'OP_ADDRESS':           4,
  'OP_READDRESS':         5,
  'OP_HIGHEST':           6,
  'OP_BAUD':              7,
  'OP_UNROOT':            8,

  'OP_HASH':              9,
  'OP_NONCE':             10,
  'OP_ABORT':             11,
  'OP_STATUS':            12,
  'OP_GPIO':              13,
  'OP_CONFIG':            14,
  'OP_STATISTICS':        15,
  'OP_GROUP':             16,
  'OP_CLOCKGATE':         17,

  # Factory Codes
  'OP_SERIAL':            50, # Serial number read/write
  'OP_LIMITS':            51, # Operational limits read/write
  'OP_HISTORY':           52, # Read operational history data
  'OP_CHARACTERIZE':      53, # Characterize one or more die
  'OP_CHAR_RESULT':       54, # Characterization result
  'OP_SETTINGS':          55, # Read or write settings
  'OP_FAN_SETTINGS':      56,
  'OP_POWER':             57,
  'OP_BAD_CORE':          58, # Set or clear bad core status
  
  # USB interface specific operation codes
  'OP_USB_INIT':          128, # Initialize USB interface details
  'OP_GET_TRACE':         129, # Send back the trace buffer if present
  'OP_LOOPBACK_USB':      130,
  'OP_LOOPBACK_UART':     131,
  'OP_DFU':               132, # Jump into the boot loader
  'OP_USB_SHUTDOWN':      133, # Initialize USB interface details
  'OP_DIE_STATUS':        134, # Die status. There are 4 die per ASIC
  'OP_GWQ_STATUS':        135, # Global Work Queue protocol status
  'OP_WORK_RESTART':      136, # Stratum work restart regime
  'OP_USB_STATS1':        137, # Statistics class 1
  'OP_USB_GWQSTATS':      138, # GWQ protocol statistics
  'OP_USB_NOTICE':        139, # Asynchronous notification event
  'OP_PING':              140, # Echo
  'OP_CORE_MAP':          141, # Return core map
  'OP_VERSION':           142, # Version information
  'OP_FAN':               143, # Set Fan Speed
  'OP_NAME':              144, # System name write/read
  'OP_USB_DEBUG':         255
}

opnames = {}
for opcode_name, opcode in opcodes.items():
  assert opcode not in opnames
  opnames[opcode] = opcode_name

known_opcodes = set(opcodes.keys())
known_opnames = set(opnames.keys())

def check_framebytes(framebytes):
  assert {x >= 0 and x < 256 for x in framebytes} == set([True])
  assert len(framebytes) >= 8
  assert framebytes[0] == 0xaa
  assert framebytes[7] == crc.crc8(framebytes[1:7])
  if framebytes[6] == 0:
    assert len(framebytes) == 8
  else:
    data_length = 4 * framebytes[6]
    # Eight byte frame header, data, plus 4 crc32 bytes.
    # Fix: Restore when using serial line directly
    # expected_framebytes_length = 8 + data_length + 4
    expected_framebytes_length = 8 + data_length
    assert expected_framebytes_length == len(framebytes)
    data = framebytes[8:8+data_length]
# Fix: Restore when using serial line directly
#        crc32 = framebytes[-4:]
#        if crc32 != crc.crc32_to_bytelist(crc.crc32(data)):
#            raise HF_Error("Bad CRC32 checksum.")

class hf_frame_data(with_metaclass(ABCMeta, object)):
  def __init__(self, bytes=None):
    self.initialize()
    if bytes is None:
      self.generate_frame_data()
    else:
      self.parse_frame_data(bytes)

  @abstractmethod
  def initialize(self):
    pass
  @abstractmethod
  def parse_frame_data(self, bytes):
    pass
  @abstractmethod
  def generate_frame_data(self):
    pass

class hf_frame_data_base(hf_frame_data):
  LENGTH = 0

  def intialize(self):
    pass
      
  def parse_frame_data(self, bytes):
    assert len(bytes) >= self.LENGTH

  def generate_frame_data(self):
    self.frame_data = [0x00]
    return self.frame_data

# Fix: Document terminology: frame is the whole thing and consists of up to
#      three parts: the header, the data, and the CRC32 checksum.
# Fix: Wants to verify checksums and throw exception if they are not right.
#      And check for 0xaa.
# Fix: Wants to make all the fields of the header accessible, but also provide raw bytes.
# Fix: Should be able to initialize with stream of bytes or by filling in fields
#      and asking for the bytes.  Throw exception if field values are out of bounds.
# Fix: Maybe want something which checks for known opcode and whether fields are
#      plausible for that opcode -- problem is that if we are using this to report
#      what was seen on the wire, we need to make those assumptions, maybe.
# Fix: The really pure way to do this is to create a subclass for every opcode type
#      and then have specific methods for that type.  Probably more trouble than
#      its worth, but it would also let us have specific methods for parameters
#      that just occupy a couple bits.
class HF_Frame():
  def __init__(self, initial_state):
    self.initialize()
    if initial_state is None:
      pass
    elif isinstance(initial_state, list):
      self.off_the_wire(initial_state)
    elif isinstance(initial_state, dict):
      self.buildframe(initial_state)
    else:
      raise HF_Error("Argument type not supported: %s" % (inital_state))

  def initialize(self):
    self.framebytes = []
    self.operation_code = None
    self.chip_address = 0
    self.core_address = 0
    self.hdata = 0
    self.data_length_field = 0
    self.crc8 = 0
    self.data = None
# Fix: Restore when using serial line directly
#        self.crc32 = None
    self.data_length = 0;

  def off_the_wire(self, framebytes):
    check_framebytes(framebytes)
    self.framebytes = framebytes
    self.operation_code = framebytes[1]
    self.chip_address = framebytes[2]
    self.core_address = framebytes[3]
    self.hdata = lebytes_to_int(framebytes[4:6])
    self.data_length_field = framebytes[6]
    self.data_length = 4 * self.data_length_field
    self.crc8 = framebytes[7]
    if self.data_length > 0:
      assert {x >= 0 and x < 256 for x in framebytes} == set([True])
      self.data = framebytes[8:8+self.data_length]
# Fix: Restore when using serial line directly
#            self.crc32 = framebytes[8+self.data_length:]

  def set_data(self, data):
    self.data = data
    self.data_length = len(data)
    self.data_length_field = int(self.data_length / 4)
# Fix: Restore when using serial line directly
#       self.crc32 = crc.crc32(self.data)

  def construct_framebytes(self):
    crc8_input  = [self.operation_code]
    crc8_input += [self.chip_address]
    crc8_input += [self.core_address]
    crc8_input += int_to_lebytes(self.hdata, 2)
    crc8_input += [self.data_length_field]
    self.crc8 = crc.crc8(crc8_input)
    frameheader = [0xaa, self.operation_code, self.chip_address, self.core_address] + \
      int_to_lebytes(self.hdata, 2) + [self.data_length_field, self.crc8]
    if self.data_length > 0:
# Fix: Restore when using serial line directly
#            return frameheader + self.data + crc.crc32_to_bytelist(self.crc32)
      self.framebytes = frameheader + self.data
    else:
      self.framebytes = frameheader
    return self.framebytes

  def buildframe(self, framedict):
    legal_fields = set(['operation_code', 'chip_address', 'core_address', 'hdata', 'data'])
    received_fields = set(framedict.keys())
    assert received_fields.issubset(legal_fields)
    assert 'operation_code' in framedict
    assert framedict['operation_code'] in opnames
    self.operation_code = framedict['operation_code']
    if 'chip_address' in framedict:
      if framedict['chip_address'] < 0 or framedict['chip_address'] > 255:
        raise HF_Error("chip_address is out of range: %d" % (framedict['chip_address']))
      self.chip_address = framedict['chip_address']
    if 'core_address' in framedict:
      if framedict['core_address'] < 0 or framedict['core_address'] > 255:
        raise HF_Error("core_address is out of range: %d" % (framedict['core_address']))
      self.core_address = framedict['core_address']
    if 'hdata' in framedict:
      if framedict['hdata'] < 0 or framedict['hdata'] > 65535:
        raise HF_Error("hdata is out of range: %d" % (framedict['hdata']))
      self.hdata = framedict['hdata']
    if 'data' in framedict:
      assert len(framedict['data']) == 0 or {x >= 0 and x < 256 for x in framedict['data']} == set([True])
      assert len(framedict['data']) <= 1020 and len(framedict['data']) % 4 == 0
      if len(framedict['data']) > 0:
        self.set_data(framedict['data'])
    return self.construct_framebytes()

  def __str__(self):
    string  = ""
    #string += "framebytes:        {}\n".format(self.framebytes)
    string += "operation_code:      {:#x}\n".format(self.operation_code)
    string += "chip_address:        {:#x}\n".format(self.chip_address)
    string += "core_address:        {:#x}\n".format(self.core_address)
    string += "hdata:               {:#x}\n".format(self.hdata)
    string += "data_length_field:   {}\n".format(self.data_length)
    #string += "data:              {}\n".format(self.data)
    return string