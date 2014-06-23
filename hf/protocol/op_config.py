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

class hf_config_data(hf_frame_data):
  LENGTH = 16

  def initialize(self):
    self.status_period                  = 0
    self.enable_periodic_status         = 1
    self.send_status_on_core_idle       = 1
    self.send_status_on_pending_empty   = 1
    self.pwm_active_level               = 0
    self.forward_all_privileged_packets = 0
    self.status_batch_delay             = 0
    self.watchdog                       = 0
    self.disable_sensors                = 0
    self.rx_header_timeout              = 0
    self.rx_ignore_header_crc           = 0
    self.rx_data_timeout                = 0
    self.rx_ignore_data_crc             = 0
    self.statistics_interval            = 0
    self.stats_diagnostic               = 0
    self.measure_interval               = 0
    self.one_usec                       = 0
    self.max_nonces_per_frame           = 0
    self.voltage_sample_points          = 0
    self.pwm_phases                     = 0
    self.trim                           = 0
    self.clock_diagnostic               = 0
    self.forward_all_packets            = 0
    self.pwm_period                     = 0
    self.pwm_pulse_period               = 0
      
  def parse_frame_data(self, bytes):
    assert len(bytes) >= self.LENGTH
    first = lebytes_to_int(bytes[0:2])
    self.status_period                  = ((0x07ff & first))
    self.enable_periodic_status         = ((0x0800 & first) >> 11)
    self.send_status_on_core_idle       = ((0x1000 & first) >> 12)
    self.send_status_on_pending_empty   = ((0x2000 & first) >> 13)
    self.pwm_active_level               = ((0x4000 & first) >> 14)
    self.forward_all_privileged_packets = ((0x8000 & first) >> 15)
    self.status_batch_delay             = bytes[2]
    self.watchdog                       = ((bytes[3] & 0x7f))
    self.disable_sensors                = ((bytes[3] & 0x80) >> 7)
    self.rx_header_timeout              = ((bytes[4] & 0x7f))
    self.rx_ignore_header_crc           = ((bytes[4] & 0x80) >> 7)
    self.rx_data_timeout                = ((bytes[5] & 0x7f))
    self.rx_ignore_data_crc             = ((bytes[5] & 0x80) >> 7)
    self.statistics_interval            = ((bytes[6] & 0x7f))
    self.stats_diagnostic               = ((bytes[6] & 0x80) >> 7)
    self.measure_interval               = bytes[7]
    second = lebytes_to_int(bytes[8:12])
    self.one_usec                       = ((second & 0x00000fff))
    self.max_nonces_per_frame           = ((second & 0x0000f000) >> 12)
    self.voltage_sample_points          = ((second & 0x00ff0000) >> 16)
    self.pwm_phases                     = ((second & 0x03000000) >> 24)
    self.trim                           = ((second & 0x3c000000) >> 26)
    self.clock_diagnostic               = ((second & 0x40000000) >> 30)
    self.forward_all_packets            = ((second & 0x80000000) >> 31)
    self.pwm_period                     = lebytes_to_int(bytes[12:14])
    self.pwm_pulse_period               = lebytes_to_int(bytes[14:16])

  def generate_frame_data(self):
    self.frame_data  = int_to_lebytes(self.status_period | (self.enable_periodic_status << 11) | (self.send_status_on_core_idle << 12) | (self.send_status_on_pending_empty << 13) | (self.pwm_active_level << 14) | (self.forward_all_privileged_packets << 15))
    self.frame_data += [self.status_batch_delay]
    self.frame_data += [self.watchdog | (self.disable_sensors << 7)]
    self.frame_data += [self.rx_header_timeout | (self.rx_ignore_header_crc << 7)]
    self.frame_data += [self.rx_data_timeout | (self.rx_ignore_data_crc << 7)]
    self.frame_data += [self.statistics_interval | (self.stats_diagnostic << 7)]
    self.frame_data += [self.measure_interval]
    self.frame_data += int_to_lebytes(self.one_usec | (self.max_nonces_per_frame << 12) | (self.voltage_sample_points << 16) | (self.pwm_phases << 24) | (self.trim << 26) | (self.clock_diagnostic << 30) | (self.forward_all_packets << 31))
    self.frame_data += int_to_lebytes(self.pwm_period)
    self.frame_data += int_to_lebytes(self.pwm_pulse_period)
    return self.frame_data

  def __str__(self):
    string  = "hf_config_data\n"
    string += "Status Period            {0} msec\n".format(self.status_period)
    string += "Enable Periodic Status   {0}\n".format(self.enable_periodic_status)
    string += "Status on Core Idle      {0}\n".format(self.send_status_on_core_idle)
    string += "Status on Pending Empty  {0}\n".format(self.send_status_on_pending_empty)
    string += "PWM Active Level         {0}\n".format(self.pwm_active_level)
    string += "Forward All Privileged   {0}\n".format(self.forward_all_privileged_packets)
    string += "Status Batch Delay       {0} msec\n".format(self.status_batch_delay)
    string += "Watchdog Timer           {0} sec\n".format(self.watchdog)
    string += "Disable Sensors          {0}\n".format(self.disable_sensors)
    string += "Header Timeout           {0} char times\n".format(self.rx_header_timeout)
    string += "Ignore Header CRC        {0}\n".format(self.rx_ignore_header_crc)
    string += "Data Timeout             {0} char times / 16\n".format(self.rx_data_timeout)
    string += "Ignore Data CRC          {0}\n".format(self.rx_ignore_data_crc)
    string += "Statistics Interval      {0} sec\n".format(self.statistics_interval)
    string += "Statistics Diagnostic    {0}\n".format(self.stats_diagnostic)
    string += "Measure Interval         {0} msec\n".format(self.measure_interval)
    string += "LF Clocks per usec       {0}\n".format(self.one_usec)
    string += "Max Nonces Per Frame     {0}\n".format(self.max_nonces_per_frame)
    string += "Voltage Sample Points    {0}\n".format(self.voltage_sample_points)
    string += "PWM Phases               {0}\n".format(self.pwm_phases)
    string += "Temperature Trim         {0}\n".format(self.trim)
    string += "Clock Diagnostic         {0}\n".format(self.clock_diagnostic)
    string += "Forward All              {0}\n".format(self.forward_all_packets)
    string += "PWM Period               {0}\n".format(self.pwm_period)
    string += "PWM Pulse Period         {0}\n".format(self.pwm_pulse_period)
    return string

class HF_OP_CONFIG(HF_Frame):
  def __init__(self, bytes=None, chip_address=0xFF, thermal_limit=105, tacho=1, thermal=1, write=1):
    if bytes is None:
      config_opt = thermal_limit | (tacho << 13) | (thermal << 14) | (write << 15)
      HF_Frame.__init__(self,{'operation_code': opcodes['OP_CONFIG'],
                              'chip_address'  : chip_address,
                              'hdata'         : config_opt })
    else:
      HF_Frame.__init__(self, bytes)
      self.config = hf_config_data(self.bytes[0:16])