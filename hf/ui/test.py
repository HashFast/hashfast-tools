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

import sys
from base import BaseUI
from datetime import datetime
import time

class TestUI(BaseUI):

  def setup_ui(self):
    # column 0
    self.setup_log(   0, 0)
    # column 2
    self.setup_logo(  2, 1, "Test UI", "v0.1")
    self.setup_module(2, 16, nasic=1)
    self.setup_input( 2, 8 )
    self.setup_output(2, 12)
    self.setup_stats( 2, 42)
    # column 7
    self.setup_info(  7, 1 )

  def update_ui(self):
    self.update_module()
    self.update_info()

  def refresh_ui(self):
    pass

def main(argv):
  hfui = TestUI()
  try:
    hfui.setup()
    hfui.refresh()

    ret = hfui.prompt("HashFast Profiling Tool. Type 'i' for interactive mode, 'a' for automatic. Type 'q' to quit.", "ai")

  finally:
    hfui.end()

if __name__ == "__main__":
   main(sys.argv[1:])
