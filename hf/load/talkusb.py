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

from ..errors import HF_NotConnectedError

INIT = 0
SHUTDOWN = 1
SEND = 2
RECEIVE = 3
SEND_MAX = 4
RECEIVE_MAX = 5

epr = None
epw = None
dev = None

def talkusb_init():
  global epr
  global epw
  global dev

  dev = None
  idVendor = None
  idProduct = None

  # HashFast idVendor
  if idVendor is None:
    idVendor = 0x297c
  # HashFast idProduct
  if idProduct is None:
    idProduct = 0x0001
  # find our device
  dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
  # was it found?
  if dev is None:
    raise HF_NotConnectedError('Device not found')
  # set the active configuration. With no arguments, the first
  # configuration will be the active one
  #dev.set_configuration()
  # get an endpoint instance
  #cfg = dev.get_active_configuration()
  #intf = cfg[(0,0)]


  # loop through configurations
  #   lsusb -v -d 297C:0001
  string = ""
  for cfg in dev:
    string += "ConfigurationValue {0}\n".format(cfg.bConfigurationValue)
    for intf in cfg:
      string += "\tInterfaceNumber {0},{0}\n".format(intf.bInterfaceNumber, intf.bAlternateSetting)
      for ep in intf:
        string += "\t\tEndpointAddress {0}\n".format(ep.bEndpointAddress)
  #print(string)

  epw = usb.util.find_descriptor(
      intf,
      # match the first OUT endpoint
      custom_match = \
      lambda e: \
          usb.util.endpoint_direction(e.bEndpointAddress) == \
          usb.util.ENDPOINT_OUT
  )

  #print("Write EndpointAddress {0}\n".format(epw.bEndpointAddress))
  assert epw is not None

  epr = usb.util.find_descriptor(
      intf,
      # match the first IN endpoint
      custom_match = \
      lambda e: \
          usb.util.endpoint_direction(e.bEndpointAddress) == \
          usb.util.ENDPOINT_IN
  )
  #print("Read EndpointAddress {0}\n".format(epr.bEndpointAddress))
  assert epr is not None

  if dev.is_kernel_driver_active(intf.bInterfaceNumber):
    dev.detach_kernel_driver(intf)
    #print("Detached Kernel Driver")

def talkusb_shutdown():
  #dev.reset()
  #usb.util.dispose_resources(dev)
  global epr
  global epw
  global dev
  dev = None
  epr = None
  epw = None

def talkusb(action, usbBuffer, usbBufferLen):
  try:
    s = time.time()
    if action is SEND:
      ret = epw.write(usbBuffer, 0)
      #print("SEND: "+str(time.time()-s))
      return ret
    if action is RECEIVE:
      ret = epr.read(usbBufferLen, 0)
      #print("RECEIVE: "+str(time.time()-s))
      return ret
    if action is INIT:
      talkusb_init()
      return 0
    if action is SHUTDOWN:
      talkusb_shutdown()
      return 0
    if action is SEND_MAX:
      return 64
    if action is RECEIVE_MAX:
      return 64
  except usb.core.USBError as e:
    # USB error numbers are negative
    #return e.errno
    raise

def init():
  try:
    talkusb_init()
  except usb.core.USBError as e:
    # USB error numbers are negative
    #return e.errno
    raise

def shutdown():
  try:
    talkusb_shutdown()
  except usb.core.USBError as e:
    # USB error numbers are negative
    #return e.errno
    raise

def send(usbBuffer):
  try:
    s = time.time()
    ret = epw.write(usbBuffer, 0)
    #print("SEND: "+str(time.time()-s))
    return ret
  except usb.core.USBError as e:
    # USB error numbers are negative
    #return e.errno
    raise

def receive(usbBufferLen):
  try:
    s = time.time()
    ret = epr.read(usbBufferLen, 0)
    #print("SEND: "+str(time.time()-s))
    return ret
  except usb.core.USBError as e:
    # USB error numbers are negative
    #return e.errno
    raise

def send_max():
  return 64

def receive_max():
  return 64
