#!/usr/bin/env python3

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

import argparse

def parse_args():
  parser = argparse.ArgumentParser(description='Package a specific HashFast tool for distribution.')
  parser.add_argument('-s', '--soak', dest='soak', action='store_true', help='package soak tool')
  parser.add_argument('-a', '--auto-profiler', dest='autoprofiler', action='store_true', help='package auto-profiler tool')
  parser.add_argument('-f', '--hftool', dest='hftool', action='store_true', help='package hftool')
  parser.add_argument('-z', '--zip', dest='zip', action='store_true', help='gzip each package')
  return parser.parse_args()

if __name__ == '__main__':
  # parse args before other imports
  args = parse_args()

import sys
import time
import datetime
import os
import tarfile
import shutil

def main(args):

  packages = []

  if args.soak:
    packages.append("soak")
  if args.autoprofiler:
    packages.append("auto-profiler")
  if args.hftool:
    packages.append("hftool")
  
  for package in packages:
    package_python(package, args.zip)

def package_python(package, package_zip=False):

  cwd = os.getcwd()
  package_dir = "hashfast-{0}-{1}".format(package, datetime.datetime.now().strftime("%Y-%m-%d"))

    # make output 
  try:
    os.mkdir(package_dir)
  except OSError:
    print("unable to make package directory")

  try:
    shutil.copy("{}.py".format(package), package_dir)
  except:
    print("unable to copy file")

  try:
    shutil.copy("README-{}".format(package), package_dir)
  except:
    print("unable to copy readme")

  try:
    shutil.copy("LICENSE", package_dir)
  except:
    print("unable to copy license")

  try:
    shutil.copytree("hf", "{0}/hf".format(package_dir))
  except:
    print("unable to copy hf package")

  if package_zip:
    tar = tarfile.open("{}.tar.gz".format(package_dir), "w:gz")
    tar.add(package_dir)
    tar.close()

if __name__ == "__main__":
   main(args)
