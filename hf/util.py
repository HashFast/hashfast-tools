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


# from http://pythonhosted.org/six/
def with_metaclass(meta, *bases):
  """Create a base class with a metaclass."""
  return meta("NewBase", bases, {})

def lebytes_to_int(lebytes):
  assert ({x >= 0 and x < 256 for x in lebytes} == set([True]))
  accum = 0
  pow = 1
  while lebytes:
    accum = accum + pow * lebytes[0]
    pow = 256 * pow
    lebytes = lebytes[1:]
  return accum

def int_to_lebytes(integer, digit):
  assert digit > 0
  assert integer >= 0 and integer < 256 ** digit
  result = []
  for i in range(digit):
    result = result + [integer % 256]
    integer = integer >> 8
  return result

def bebytes_to_int(bebytes):
  assert ({x >= 0 and x < 256 for x in bebytes} == set([True]))
  result = 0
  for x in bebytes:
    result = 256*result + x
  return result

def int_to_bebytes(integer, digit):
  assert digit > 0
  assert integer >= 0 and integer < 256 ** digit
  lebytes = int_to_lebytes(integer, digit)
  lebytes.reverse()
  return lebytes

def reverse_every_four_bytes(bytelist):
    assert len(bytelist) % 4 == 0
    assert {x >= 0 and x < 256 for x in bytelist} == set([True])
    result = []
    for i in range(int(len(bytelist)/4)):
        a = bytelist[4*i:4*i+4]
        a.reverse()
        result = result + a
    return result


# ScoutUserName - The full name of the FogBugz user the case creation or edit should be made as.
# ScoutProject  - The Project that new cases should be created in (must be a valid project name).
# ScoutArea     - The Area that new cases should go into (must be a valid area in the ScoutProject).
# Description   - This is the unique string that identifies the particular crash that has just occurred.
# Extra         - The details about this particular crash.
# Email         - An email address to associate with the report, often the customer's email.
def fogbugz_report(description, extra, project="Software", area="Test Support"):
  username = 'AutoBug Tracking'
  url      = 'https://hashfast.fogbugz.com/scoutSubmit.asp'
  try:
    # python 3
    from urllib.parse   import urlencode
    from urllib.request import urlopen
    params = urlencode({'ScoutUserName':username, 'ScoutProject':project, 'ScoutArea':area, 'Description':description, 'Extra':extra})
    data   = params.encode('ascii')
    f      = urlopen(url, data)
    return f.read()
  except ImportError:
    # python 2
    from urllib         import urlencode
    from urllib         import urlopen
    params = urlencode({'ScoutUserName':username, 'ScoutProject':project, 'ScoutArea':area, 'Description':description, 'Extra':extra})
    f      = urlopen(url, params)
    return f.read()

