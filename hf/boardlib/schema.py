"""Dictionary of schema names and functions to test schema."""

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

# Implementation note: The package json_schema was not used because it
# is currently incomplete, no license for it is defined, it is less
# general than writing our own test functions, and it is overkill.
# https://pypi.python.org/pypi/json_schema

# A schema should never be modified.  Instead, add a new one with a
# check function.

class SchemaError(Exception):
    """SchemaError: just an exception to flag errors in this module."""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def check_alpha_schema(datadict):
    """Check validity of Alpha schema.

    Returns True on success, throws an exception on error.
    """

    if not isinstance(datadict, dict):
        raise SchemaError("Did not receive a dictionary.")
    fields = ['serial', 'board_id', 'test_result', 'manual_check', 'firmware_version',
              'average_hashrate', 'accepted_shares', 'hardware_errors']
    fields.sort()
    dict_fields = list(datadict)
    dict_fields.sort()
    if fields != dict_fields:
        raise SchemaError("Expected fields (%s) did not match fields we got (%s)."
                          % (str(fields), str(dict_fields)))
    if not isinstance(datadict['serial'], str):
        raise SchemaError("Field 'serial' is not a string.")
    if not isinstance(datadict['board_id'], str):
        raise SchemaError("Field 'board_id' is not a string.")
    if not isinstance(datadict['test_result'], str):
        raise SchemaError("Field 'test_result' is not a string.")
    if not isinstance(datadict['manual_check'], str):
        raise SchemaError("Field 'manual_check' is not a string.")
    if not isinstance(datadict['firmware_version'], str):
        raise SchemaError("Field 'firmware_version' is not a string.")
    if not isinstance(datadict['average_hashrate'], int):
        raise SchemaError("Field 'average_hashrate' is not an integer.")
    if not isinstance(datadict['accepted_shares'], int):
        raise SchemaError("Field 'accepted_shares' is not an integer.")
    if not isinstance(datadict['hardware_errors'], int):
        raise SchemaError("Field 'hardware_errors' is not an integer.")
    return True

def check_pepper_schema(datadict):
    """Check validity of Pepper schema.

    Returns True on success, throws an exception on error.
    """

    if not isinstance(datadict, dict):
        raise SchemaError("Did not receive a dictionary.")
    fields = ['serial', 'module_id', 'test_result', 'hash_rate', 'hash_clock', 'voltage', 'cycles', 'firmware']
    fields.sort()
    dict_fields = list(datadict)
    dict_fields.sort()
    if fields != dict_fields:
        raise SchemaError("Expected fields (%s) did not match fields we got (%s)."
                          % (str(fields), str(dict_fields)))
    if not isinstance(datadict['serial'], str):
        raise SchemaError("Field 'serial' is not a string.")
    if not isinstance(datadict['module_id'], str):
        raise SchemaError("Field 'module_id' is not a string.")
    if not isinstance(datadict['test_result'], str):
        raise SchemaError("Field 'test_result' is not a string.")
    if not isinstance(datadict['hash_rate'], int):
        raise SchemaError("Field 'hash_rate' is not an integer.")
    if not isinstance(datadict['hash_clock'], int):
        raise SchemaError("Field 'hash_clock' is not an integer.")
    if not isinstance(datadict['voltage'], int):
        raise SchemaError("Field 'voltage' is not an integer.")
    if not isinstance(datadict['cycles'], int):
        raise SchemaError("Field 'cycles' is not an integer.")
    if not isinstance(datadict['firmware'], str):
        raise SchemaError("Field 'firmware' is not a string.")
    return True

schema_dictionary = {
    'Alpha': check_alpha_schema,
    'Pepper': check_pepper_schema
    }
