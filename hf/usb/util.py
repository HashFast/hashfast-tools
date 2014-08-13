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

import time
import usb.core
import usb.util

# HashFast App:     297c:0001
USBID_HF_VID   = 0x297c
USBID_HF_PID   = 0x0001
USB_DEV_HF     = (USBID_HF_VID, USBID_HF_PID)
# HFU Boot Loader:  297c:8001
USBID_HFU_VID  = 0x297c 
USBID_HFU_PID  = 0x8001
USB_DEV_HFU    = (USBID_HFU_VID, USBID_HFU_PID)
# DFU Boot Loader:  03eb:2ff6 Atmel Corp.
USBID_DFU_VID  = 0x03eb
USBID_DFU_PID  = 0x2ff6
USB_DEV_DFU    = (USBID_DFU_VID, USBID_DFU_PID)
# dfu target
UC_PART_BASE   = 'at32uc3b0'
# all devices
all_devices    = [USB_DEV_HFU, USB_DEV_HF, USB_DEV_DFU]

HF_DEVICE_NOT_FOUND     = 'HFDevice Not Found'
HF_DEVICE_FOUND         = 'HFDevice Found!'

def noprint(x):
  pass

def poll_hf_device(devices=all_devices, intv=1, printer=noprint):
  while 1:
    time.sleep(intv)
    for device in devices:
      try:
        idVendor  = device[0]
        idProduct = device[1]
        dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        if dev is not None:
          printer(HF_DEVICE_FOUND)
          return device
      except:
        printer(HF_DEVICE_NOT_FOUND)
