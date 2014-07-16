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

import subprocess
import shutil
import time
import os

from hf.errors   import HF_ChecksumError, HF_UpdateError
from hf.usb.util import UC_PART

class HF_Updater():

  def __init__(self):
    self.dev            = None
    self.modules        = None
    # dependencies
    pathlist = [".", ".."]
    os.environ["PATH"] += os.pathsep + os.pathsep.join(pathlist)
    try:
      from shutil import which
    except:
      def which(pgm):
        path=os.getenv('PATH')
        for p in path.split(os.path.pathsep):
          p=os.path.join(p,pgm)
          if os.path.exists(p) and os.access(p,os.X_OK):
            return p
    self.SHA256SUM      = which('sha256sum')
    if self.SHA256SUM is None:
      print("WARNING - sha256sum is not on path. Cannot verify checksums.")
    self.HFUPDATE       = which('hfupdate')
    if self.HFUPDATE is None:
      print("WARNING - hfupdate is not on path. Cannot update firmware.")
    self.DFU_PROGRAMMER = which('dfu-programmer')
    if self.DFU_PROGRAMMER is None:
      print("WARNING - dfu-programmer is not on path. Cannot update bootloader.")

  def fetch_release_firmwares(self):
    url = 'https://gist.github.com/HF-SW-Team/224b2a8d746007ec5851/raw/firmware-release.json'
    try:
      # python 3
      from urllib.request import urlopen
      from simplejson     import load
      f = urlopen(url)
      return load(f)
    except ImportError:
      # python 2
      from urllib         import urlopen
      from simplejson     import load
      f = urlopen(url)
      return load(f)

  def list_release_firmwares(self):
    hfr = self.fetch_release_firmwares()
    print("")
    print("Releases last updated: {}".format(hfr['updated']))
    for r in hfr['releases']:
      print(r['version'])

  def fetch_release_firmware(self, release=None):
    hfr = self.fetch_release_firmwares()
    if release is None:
      release = hfr['latest']
    for r in hfr['releases']:
      if r['version'] == release:
        return self.fetch_file(r['hfu'])
    raise HF_UpdateError("Release not found! Use --list to find.")

  def fetch_release_bootloader(self, release=None):
    hfr = self.fetch_release_firmwares()
    if release is None:
      release = hfr['latest']
    for r in hfr['releases']:
      if r['version'] == release:
        return self.fetch_file(r['dfu'])

  def fetch_debug_builds(self):
    url = 'https://gist.github.com/HF-SW-Team/224b2a8d746007ec5851/raw/firmware-debug.json'
    try:
      # python 3
      from urllib.request import urlopen
      from simplejson     import load
      f = urlopen(url)
      return load(f)
    except ImportError:
      # python 2
      from urllib         import urlopen
      from simplejson     import load
      f = urlopen(url)
      return load(f)

  def fetch_debug_build(self, build=None):
    hfb = self.fetch_debug_builds()
    for b in hfb['builds']:
      if b['build'] == build:
        return self.fetch_file(b['hfu'])
    raise HF_UpdateError("Build not found! Use --debug --list to find.")

  def list_debug_builds(self):
    hfb = self.fetch_debug_builds()
    print("")
    print("Debug builds last updated: {}".format(hfb['updated']))
    for b in hfb['builds']:
      print(b['build'])

  def get_checksum(self, path):
    return subprocess.check_output([self.SHA256SUM, path])

  def fetch_file(self, fid, checksum=False):
    # report hook
    def report_hook(block_count, block_size, total_size):
      print(block_count, block_size, total_size)
    # fetch_file
    print("")
    print("Fetching file...")
    url = "https://drive.google.com/uc?export=download&id={}".format(fid)
    try:
      # python 3
      from urllib.request import urlretrieve
      (filename, headers) = urlretrieve(url, reporthook=report_hook)
      print("Got file!")
      if checksum:
        if self.get_checksum(filename) != checksum:
          raise HF_ChecksumError()
      return filename
    except ImportError:
      # python 2
      from urllib         import urlretrieve
      (filename, headers) = urlretrieve(url, reporthook=report_hook)
      print("Got file!")
      if checksum:
        if self.get_checksum(filename) != checksum:
          raise HF_ChecksumError()
      return filename

  def enter_loader(self, module=0):
    print("\nEntering Loader Mode...")
    self.dev.reboot(module, 0x0001)
    time.sleep(3)

  def enter_app(self, module=0):
    print("\nEntering Application Mode...")
    subprocess.check_call([self.HFUPDATE, '-r'])
    time.sleep(3)

  def read_version(self, module=0):
    return self.dev.version(module)

  def read_serial(self, module=0):
    return self.dev.serial(module)

  def enumerate_modules(self):
    self.dev.power_set(0, 1)
    time.sleep(3)
    print("")
    config = self.dev.config()
    self.modules = config.modules
    print(  "Modules found: {}".format(config.modules))
    print(  "")
    for module in range(self.modules):
      serial  = self.dev.serial(module)
      print("Module {0} ({1})".format(module, serial.hfserial()))
      version = self.dev.version(module)
      print("  current version: {0} crc: {1:#x}".format(version.version, version.crc))

  def load_firmware_hfu(self, hfu_file):
    for module in range(self.modules):
      print("")
      print("Updating module {}...".format(module))
      subprocess.check_call([self.HFUPDATE, '-m%d' % module, hfu_file])

  def load_firmware_dfu(self, hex_file):
    subprocess.check_call([self.DFU_PROGRAMMER, UC_PART, 'erase'])
    subprocess.check_call([self.DFU_PROGRAMMER, UC_PART, 'flash', '--suppress-bootloader-mem', hex_file])
    subprocess.check_call([self.DFU_PROGRAMMER, UC_PART, 'reset'])