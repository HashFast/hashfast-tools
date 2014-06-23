"""Library of stuff related to board test functions."""

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

import hashlib
import json
import math
import os
import re
import socket
import stat
import subprocess
import time

from hf.boardlib.schema import schema_dictionary

sync_path = '/bin/sync'
tempfilebase = 'tempfile'

if not os.path.exists(sync_path):
    sys.stderr.write("The internal value sync_path (%s) does not exist.\n"
                     % (sync_path))
    sys.exit(1)

if not os.path.isfile(sync_path):
    sys.stderr.write("The internal value sync_path (%s) is not a file or "
                     "a link to a file.\n" % (sync_path))
    sys.exit(1)

class BoardLibError(Exception):
    """BoardLibError: just an exception to flag errors in this module."""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class BoardData:
    """BoardData holds state required to write records to a simple database.

    Records are stored one at a time and stored in individual files in
    a data directory.  Records consist of any Python data structure
    that can be represented with JSON.  The records are stored in a
    header structure which provides meta-information.

    Files in the data directory are given a unique name.  (See
    create_unique_file().)

    The header is a Python dictionary with these fields.  ("*" indicates
    that the field is also a field in the BoardData instance.):
    schema: the name of a schema from schema.py.
    hostname*: name of the host on which the record is created.
    absdatadir*: the absolute path of the data directory on the original
      machine where this record was written.  Note that this will likely
      be different on the machine where the records are ultimately stored
      and processed.
    sequence_number*: sequence number of records created by a particular
      process, beginning with 0.
    most_recent*: name of the most recent file written by this process.
    most_recent_hash*: SHA-256 hash of the most recent file written by
      this process.
    last_process_most_recent*: Name of what this process thinks was the
      last file written by the previous process.  Only defined for the
      first record written by this process.
    last_process_most_recent_hash*: SHA-256 hash of the last_process_most_recent
      file.
    payload: any Python data structure which may be represented using JSON,
       but will usually be a dictionary.
    """

    def __init__(self, datadir):
        """Initialize the BoardData instance using datadir as the directory to store data."""
        self.absdatadir = os.path.abspath(datadir)
        valid_datadir(self.absdatadir)
        # Test datadir's viability.
        temp = create_unique_file(self.absdatadir)
        os.remove(temp)
        self.hostname = socket.gethostname()
        self.sequence_number = 0
        self.last_process_most_recent = most_recent_unique_file(self.absdatadir)
        if self.last_process_most_recent:
            self.last_process_most_recent_hash = \
                file_hash_sha256(os.path.join(self.absdatadir,
                                              self.last_process_most_recent))
        else:
            self.last_process_most_recent_hash = None
        self.most_recent = None
        self.most_recent_hash = None

    def Store(self, payload, schema):
        """Stores payload conforming to schema."""
        # Check data directory every time.
        valid_datadir(self.absdatadir, samehost=True)
        if not schema in schema_dictionary:
            raise BoardLibError("%s is not in the schema dictionary." % (schema))
        if not schema_dictionary[schema](payload):
            raise BoardLibError("Received data structure which did not satisfy "
                                "schema %s." % (schema))
        header = {'schema': schema,
                  'hostname': self.hostname,
                  'absdatadir': self.absdatadir,
                  'sequence_number': self.sequence_number,
                  'most_recent': self.most_recent,
                  'most_recent_hash': self.most_recent_hash,
                  'last_process_most_recent': self.last_process_most_recent,
                  'last_process_most_recent_hash': self.last_process_most_recent_hash,
                  'payload': payload}
        json_header = bytes(json.dumps(header, indent=2, sort_keys=True), 'UTF-8')
        ufile = create_unique_file(self.absdatadir)
        with open(ufile, 'wb') as uf:
            uf.write(json_header)
        os.chmod(ufile, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH) # i.e. 0444
        syncsyncsync()
        self.most_recent = os.path.basename(ufile)
        d = hashlib.sha256()
        d.update(json_header)
        self.most_recent_hash = d.hexdigest()
        self.sequence_number = self.sequence_number + 1
        self.last_process_most_recent = None
        self.last_process_most_recent_hash = None
        return True

def create_unique_file(directory):
    """Creates uniquely named file in directory and returns its absolute path.

    Dan Bernstein technique: a tempfile is created which incorporates
    the pid of this process.  If one already exists, it is safely
    removed because only this process has its pid at any particular
    time.  Then, the i-node of the tempfile is read and the name
    changed to incorporate it.  This guarantees the file will be
    unique within its entire filesystem.  The hostname and a time
    stamp are also incorporated into the name to promote uniqueness if
    the file is moved to another file system or host system.

    The resulting file has form: <timestamp,secs>.<hostname>.<i-node>

    It is theoretically possible to create a file name collision if,
    within a single second, a file is created, moved to another file
    system, deleted, and then another created in its place and given
    the same i-node.
    """

    absdir = os.path.abspath(directory)
    if not os.path.exists(absdir):
        raise BoardLibError("Directory %s does not exist." % (directory))
    if not os.path.isdir(absdir):
        raise BoardLibError("Not a directory: %d." % (directory))
    tempname = tempfilebase + '.' + str(os.getpid())
    temppath = os.path.join(absdir, tempname)
    if os.path.exists(tempname):
        if os.path.isfile(tempname):
            # Safe because we are the only process with our pid.
            os.remove(tempname)
        else:
            raise BoardLibError("%s exists, but it is not a file." % (temppath))
    # Create empty file.
    with open(temppath, "wb") as tp:
        pass
    # Note: time.time() returns a floating point number!
    now = str(math.floor(time.time()))
    hostname = socket.gethostname()
    inode = str(os.stat(temppath)[stat.ST_INO])
    uniquepath = os.path.join(absdir, '.'.join([now, hostname, inode]))
    if os.path.exists(uniquepath):
        raise BoardLibError("%s exists but it should not." % (uniquepath))
    os.rename(temppath, uniquepath)
    syncsyncsync()
    return uniquepath

def syncsyncsync():
    """Calls sync three times to guarantee buffers are flushed."""

    subprocess.check_call([sync_path])
    subprocess.check_call([sync_path])
    subprocess.check_call([sync_path])

def file_hash_sha256(file):
    """Return SHA-256 hash of file as hexadecimal string."""

    with open(file, 'rb') as hf:
        hfstuff = hf.read()
    ho = hashlib.sha256()
    ho.update(hfstuff)
    return ho.hexdigest()

def most_recent_unique_file(datadir):
    """Returns most recent file of 'unique' type in datadir.

    A 'unique' has form <timestamp,secs>.<hostname>.<i-node>.
    Returns only the filename of the file, not the entire path.
    """

    absdatadir = os.path.abspath(datadir)
    if not os.path.isdir(absdatadir):
        raise BoardLibError("%s is not a directory." % (absdatadir))
    files = os.listdir(absdatadir)
    unique_files = filter(lambda x: re.match('^\d{10}\.\S+\.\d+$', x), files)
    most_recent_file = None
    most_recent_file_modtime = 0
    for ufile in unique_files:
        abs_ufile = os.path.abspath(os.path.join(absdatadir, ufile))
        ufile_modtime = os.stat(abs_ufile)[stat.ST_MTIME]
        if ufile_modtime > most_recent_file_modtime:
            most_recent_file = ufile
            most_recent_file_modtime = ufile_modtime
    return most_recent_file

# Look for anything unexpected in the data directory.
def valid_datadir(datadir, samehost=False):
    """Quick check of contents of datadir.

    If the files in datadir are on the same host where they were
    created, we can check the inode numbers and host names of the
    files.  Otherwise, we would expect these to be different.

    An exception will be thrown on error.  If the function returns,
    it succeeded.

    The datadir is expected to contain only files of the 'unique'
    format or a 'tempfile'.  (See create_unique_file()).  It is
    not expected to contain anything else.
    """
    hostname = socket.gethostname()
    absdatadir = os.path.abspath(datadir)
    if not os.path.isdir(absdatadir):
        raise BoardLibError("%s is not a directory." % (absdatadir))
    for entry in os.listdir(absdatadir):
        entry_path = os.path.abspath(os.path.join(absdatadir, entry))
        if os.path.isdir(entry_path):
            raise BoardLibError("Directory %s has a subdirectory %s."
                                % (absdatadir, entry_path))
        if os.path.isfile(entry_path):
            # <now>.<hostname>.<inode>
            unique_file_match = re.match('^\d{10}\.(\S+)\.(\d+)$', entry)
            # <tempfile>.<inode>
            tempfile_match = re.match('^' + tempfilebase + '\.(\d+)$', entry)
            if unique_file_match:
                if samehost:
                    filename_hostname = unique_file_match.group(1)
                    filename_inode = int(unique_file_match.group(2))
                    if filename_hostname != hostname:
                        raise BoardLibError("%s has host name different from "
                                            "this machine: %s" % (entry_path, hostname))
                    actual_inode = os.stat(entry_path)[stat.ST_INO]
                    if filename_inode != actual_inode:
                        raise BoardLibError("File %s claims to be inode %d but "
                                            "it really has inode %d."
                                            % (entry_path, filename_inode, actual_inode))
            elif tempfile_match:
                pass
            else:
                raise BoardLibError("Directory %s has an unexpected file: %s"
                                    % (datadir, entry_path))
        else:
            raise BoardLibError("Directory %s has entry which is not a "
                                "directory or a file: %s" % (datadir, entry_path))
        return None

def valid_datadir_intensive(datadir, samehost=False):
    """Intensively checks the validity of the records in datadir.

    Calls valid_datadir(), then confirms that references to other records
    are consistent and that the sequence numbers are consistent.

    If run on the same host where the record was created, we can do extra checking.
    """

    # Do the quick check.
    valid_datadir(datadir, samehost)
    # Now the intensive part.
    absdatadir = os.path.abspath(datadir)
    files = os.listdir(absdatadir)
    unique_files = filter(lambda x: re.match('^\d{10}\.\S+\.\d+$', x), files)
    abs_unique_files = [os.path.join(absdatadir, x) for x in unique_files]
    uf_dict = load_files(abs_unique_files)
    # Checks everything within the context of a single record.
    for uf in uf_dict:
        basic_json_check(absdatadir, uf, uf_dict[uf], samehost)
    # Checks references to other records.
    for uf in uf_dict:
        header = json.loads(str(uf_dict[uf], 'UTF-8'))
        if header['most_recent']:
            m = hashlib.sha256()
            m.update(uf_dict[header['most_recent']])
            actual_most_recent_hash = m.hexdigest()
            if actual_most_recent_hash != header['most_recent_hash']:
                raise BoardLibError("File %s reports most recent file of %s "
                                    "and most_recent_hash of %S, but actual hash "
                                    "is %s"
                                    % (uf,
                                       header['most_recent'],
                                       header['most_recent_hash'],
                                       actual_most_recent_hash))
            header_most_recent = \
                json.loads(str(uf_dict[header['most_recent']], 'UTF-8'))
            if header['sequence_number'] != header_most_recent['sequence_number'] + 1:
                raise BoardLibError("File %s sequence_number (%d) is not one more "
                                    "than file %s sequence_number (%d)."
                                    % (uf,
                                       header['sequence_number'],
                                       header['most_recent'],
                                       header_most_recent['sequence_number']))

def basic_json_check(datadir, filename, json_data, samehost=False):
    """Reads filename from datadir and does basic checking without reference to other records.

    If run on the same host where the file was created, we can do more checking.
    """
    header = json.loads(str(json_data, 'UTF-8'))
    if not isinstance(header, dict):
        raise BoardLibError("%s contains JSON which does not generate a dictionary."
                            % (filename))
    required_keys = {'schema', 'hostname', 'absdatadir', 'sequence_number',
                     'most_recent', 'most_recent_hash', 'last_process_most_recent',
                     'last_process_most_recent_hash', 'payload'}
    for header_key in list(header):
        if header_key not in required_keys:
            raise BoardLibError("%s is an unexpected key in the JSON data from %s."
                                % (header_key, filename))
    for required_key in list(required_keys):
        if not required_key in header:
            raise BoardLibError("%s is not in JSON data in file %s"
                                % (required_key, filename))
    if header['schema'] not in schema_dictionary:
        raise BoardLibError("Schema %s from file %s does not appear in the "
                            "schema dictionary." % (header['schema'], filename))
    if not isinstance(header['sequence_number'], int):
        raise BoardLibError("Filename %s holds a sequence number which is not "
                            "an integer." % (filename))
    if header['sequence_number'] < 0:
        raise BoardLibError("Sequence_number %d from file %s is negative"
                            % (header['sequence_number'], filename))
    # <now>.<hostname>.<inode>
    unique_file_match = re.match('^\d{10}\.(\S+)\.\d+$', filename)
    if unique_file_match:
        file_hostname = unique_file_match.group(1)
        if file_hostname != header['hostname']:
            raise BoardLibError("Filename %s does not match hostname in JSON: %s"
                                % (filename, header['hostname']))
    else:
        raise BoardLibError("Filename %s has the wrong structure." % (filename))
    if header['most_recent'] == None and header['sequence_number'] != 0:
        raise BoardLibError("Filename %s has no most_recent predecessor but "
                            "sequence number is non-zero: %d"
                            % (filename, header['sequence_number']))
    if header['last_process_most_recent'] and header['most_recent']:
        raise BoardLibError("Filename %s has last_process_most_recent (%s) "
                            "and most_recent (%s) defined."
                            % (filename, header['last_process_most_recent'], header['most_recent']))
    if samehost:
        hostname = socket.gethostname()
        if header['hostname'] != hostname:
            raise BoardLibError("Hostname %s from file %s is not the same "
                                "as our host: %s"
                                % (header['hostname'], filename, hostname))
        if datadir != header['absdatadir']:
            raise BoardLibError("Absdatadir %s from file %s is not the same "
                                "as the datadir we were given: %s"
                                % (header['absdatadir'], filename, datadir))
    schema_check_func = schema_dictionary[header['schema']]
    if not schema_check_func(header['payload']):
        raise BoardLibError("Filename %s failed its schema check." % (filename))
    if (header['most_recent'] and not header['most_recent_hash']) or \
            (not header['most_recent'] and header['most_recent_hash']):
        raise BoardLibError("In file %s most_recent and most_recent_hash are "
                            "not both defined." % (filename))
    if (header['last_process_most_recent'] and not header['last_process_most_recent_hash']) \
            or (not header['last_process_most_recent'] and header['last_process_most_recent_hash']):
        raise BoardLibError("In file %s last_process_most_recent and "
                            "last_process_most_recent_hash are not both defined."
                            % (filename))
    if header['most_recent_hash'] and \
            not re.match('^[0-9a-f]{64}$', header['most_recent_hash']):
        raise BoardLibError("In file %s the most_recent_hash does not look like "
                            "a valid hash: %s" % (filename, header['most_recent_hash']))
    return None

def load_files(files):
    """Return dictionary of contents of files indexed by filename."""

    uf_by_filename = {}
    for filename in files:
        basefile = os.path.basename(filename)
        with open(filename, 'rb') as uf:
            ufc = uf.read()
        uf_by_filename[basefile] = ufc
    return uf_by_filename
