#! /usr/bin/env python3

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

# requires pyusb
#   pip install --pre pyusb

import usb.core
import usb.util
import sys
import time

from hf.errors   import HF_NotConnectedError
from hf.usb.util import USBID_HF_VID, USBID_HFU_VID, USBID_DFU_VID
from hf.usb.util import USBID_HF_PID, USBID_HFU_PID, USBID_DFU_PID

HF_USBBULK_INIT         = 0
HF_USBBULK_SHUTDOWN     = 1
HF_USBBULK_SEND         = 2
HF_USBBULK_RECEIVE      = 3
HF_USBBULK_SEND_MAX     = 4
HF_USBBULK_RECEIVE_MAX  = 5

HF_BULK_DEVICE_NOT_FOUND     = 'HFBulkDevice Not Found'
HF_BULK_DEVICE_FOUND         = 'HFBulkDevice Found!'

def noprint(x):
  pass

def poll_hf_bulk_device(intv=1, printer=noprint):
  # look for device
  while 1:
    time.sleep(intv)
    try:
      dev = HFBulkDevice()
      break
    except:
      printer(HF_BULK_DEVICE_NOT_FOUND)
  # found device
  printer(HF_BULK_DEVICE_FOUND)
  return dev

class HFBulkDevice():
  def __init__(self, idVendor=None, idProduct=None):
    # HashFast idVendor
    if idVendor is None:
      idVendor = USBID_HF_VID
    # HashFast idProduct
    if idProduct is None:
      idProduct = USBID_HF_PID
    # find our device
    self.dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
    # was it found?
    if self.dev is None:
      raise HF_NotConnectedError('HF Device not found in Application Mode')

  ##
  # information about the connected device
  ##
  def info(self):
    # loop through configurations
    #   lsusb -v -d 297C:0001
    string = ""
    for cfg in self.dev:
      string += "ConfigurationValue {0}\n".format(cfg.bConfigurationValue)
      for intf in cfg:
        string += "\tInterfaceNumber {0},{0}\n".format(intf.bInterfaceNumber, intf.bAlternateSetting)
        for ep in intf:
          string += "\t\tEndpointAddress {0}\n".format(ep.bEndpointAddress)
    return string

  def init(self):
    try:
      string = ""
      # detach kernel driver
      if self.dev.is_kernel_driver_active(1):
        self.dev.detach_kernel_driver(1)
        string += "Detached Kernel Driver\n"
      # set the active configuration. With no arguments, the first
      # configuration will be the active one
      self.dev.set_configuration()
      # get an endpoint instance
      self.cfg = self.dev.get_active_configuration()
      self.intf = self.cfg[(1,0)]
      # write endpoint
      self.epw = usb.util.find_descriptor(self.intf,
          # match the first OUT endpoint
          custom_match = \
          lambda e: \
              usb.util.endpoint_direction(e.bEndpointAddress) == \
              usb.util.ENDPOINT_OUT
      )
      assert self.epw is not None
      string += "EndpointAddress for writing {}\n".format(self.epw.bEndpointAddress)
      # read endpoint
      self.epr = usb.util.find_descriptor(self.intf,
          # match the first IN endpoint
          custom_match = \
          lambda e: \
              usb.util.endpoint_direction(e.bEndpointAddress) == \
              usb.util.ENDPOINT_IN
      )
      assert self.epr is not None
      string += "EndpointAddress for reading {}\n".format(self.epr.bEndpointAddress)
      return string
    except usb.core.USBError:
      #return -1
      raise

  def shutdown(self):
    return 0

  def send(self, usbBuffer):
    try:
      ret = epw.write(usbBuffer, 0)
      return ret
    except usb.core.USBError:
      #return -1
      raise

  def recieve(self, bufferLen):
    try:
      ret = epr.read(bufferLen, 0)
      return ret
    except usb.core.USBError:
      #return -1
      raise

  def send_max(self):
    return 64

  def recieve_max(self):
    return 64
