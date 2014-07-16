#!/usr/bin/env python

# Copyright (c) 2014, HashFast Technologies LLC
# All rights reserved.
#
# based heavily upon:
#   Stratum mining proxy (https://github.com/slush0/stratum-mining-proxy)
#   Copyright (C) 2012 Marek Palatinus <slush@satoshilabs.com>
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
import time
import os
import socket

def parse_args():
  parser = argparse.ArgumentParser(description='This proxy allows you to run getwork-based miners against Stratum mining pool.')
  parser.add_argument('-c', '--clockrate', dest='clockrate', type=int, default=1, help='Miner clockrate')
  parser.add_argument('-o', '--host', dest='host', type=str, default='stratum.bitcoin.cz', help='Hostname of Stratum mining pool')
  parser.add_argument('-p', '--port', dest='port', type=int, default=3333, help='Port of Stratum mining pool')
  parser.add_argument('-sh', '--stratum-host', dest='stratum_host', type=str, default='0.0.0.0', help='On which network interface listen for stratum miners. Use "localhost" for listening on internal IP only.')
  parser.add_argument('-sp', '--stratum-port', dest='stratum_port', type=int, default=3333, help='Port on which port listen for stratum miners.')
  parser.add_argument('-oh', '--getwork-host', dest='getwork_host', type=str, default='0.0.0.0', help='On which network interface listen for getwork miners. Use "localhost" for listening on internal IP only.')
  parser.add_argument('-gp', '--getwork-port', dest='getwork_port', type=int, default=8332, help='Port on which port listen for getwork miners. Use another port if you have bitcoind RPC running on this machine already.')
  parser.add_argument('-nm', '--no-midstate', dest='no_midstate', action='store_true', help="Don't compute midstate for getwork. This has outstanding performance boost, but some old miners like Diablo don't work without midstate.")
  parser.add_argument('-rt', '--real-target', dest='real_target', action='store_true', help="Propagate >diff1 target to getwork miners. Some miners work incorrectly with higher difficulty.")
  parser.add_argument('-cl', '--custom-lp', dest='custom_lp', type=str, help='Override URL provided in X-Long-Polling header')
  parser.add_argument('-cs', '--custom-stratum', dest='custom_stratum', type=str, help='Override URL provided in X-Stratum header')
  parser.add_argument('-cu', '--custom-user', dest='custom_user', type=str, help='Use this username for submitting shares')
  parser.add_argument('-cp', '--custom-password', dest='custom_password', type=str, help='Use this password for submitting shares')
  parser.add_argument('--old-target', dest='old_target', action='store_true', help='Provides backward compatible targets for some deprecated getwork miners.')    
  parser.add_argument('--blocknotify', dest='blocknotify_cmd', type=str, default='', help='Execute command when the best block changes (%%s in BLOCKNOTIFY_CMD is replaced by block hash)')
  parser.add_argument('-t', '--test', dest='test', action='store_true', help='Run performance test on startup')    
  parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Enable low-level debugging messages')
  parser.add_argument('-q', '--quiet', dest='quiet', action='store_true', help='Make output more quiet')
  parser.add_argument('-i', '--pid-file', dest='pid_file', type=str, help='Store process pid to the file')
  parser.add_argument('-l', '--log-file', dest='log_file', type=str, help='Log to specified file')
  parser.add_argument('-st', '--scrypt-target', dest='scrypt_target', action='store_true', help='Calculate targets for scrypt algorithm')
  return parser.parse_args()

from stratum import settings
settings.LOGLEVEL='INFO'

if __name__ == '__main__':
  # We need to parse args & setup Stratum environment
  # before any other imports
  args = parse_args()
  if args.quiet:
    settings.DEBUG = False
    settings.LOGLEVEL = 'WARNING'
  elif args.verbose:
    settings.DEBUG = True
    settings.LOGLEVEL = 'DEBUG'
  if args.log_file:
    settings.LOGFILE = args.log_file
      
from twisted.internet import reactor, defer
from stratum.socket_transport import SocketTransportFactory, SocketTransportClientFactory
from stratum.services import ServiceEventHandler
from twisted.web.server import Site

from hf.mining_libs import stratum_listener
from hf.mining_libs import client_service
from hf.mining_libs import jobs
from hf.mining_libs import worker_registry
from hf.mining_libs import utils

import stratum.logger
log = stratum.logger.get_logger('proxy')

running = True

def on_shutdown(f):
  '''Clean environment properly'''
  global running
  running = False
  log.info("Shutting down proxy...")
  f.is_reconnecting = False # Don't let stratum factory to reconnect again
  
@defer.inlineCallbacks
def on_connect(f, workers, job_registry):
  '''Callback when proxy get connected to the pool'''
  log.info("Connected to Stratum pool at %s:%d" % f.main_host)
  #reactor.callLater(30, f.client.transport.loseConnection)
  
  # Hook to on_connect again
  f.on_connect.addCallback(on_connect, workers, job_registry)
  
  # Every worker have to re-autorize
  workers.clear_authorizations() 
     
  # Subscribe for receiving jobs
  log.info("Subscribing for mining jobs")
  (_, extranonce1, extranonce2_size) = (yield f.rpc('mining.subscribe', []))[:3]
  job_registry.set_extranonce(extranonce1, extranonce2_size)
  stratum_listener.StratumProxyService._set_extranonce(extranonce1, extranonce2_size)
  
  if args.custom_user:
    log.warning("Authorizing custom user %s, password %s" % (args.custom_user, args.custom_password))
    workers.authorize(args.custom_user, args.custom_password)

  defer.returnValue(f)
   
def on_disconnect(f, workers, job_registry):
  '''Callback when proxy get disconnected from the pool'''
  log.info("Disconnected from Stratum pool at %s:%d" % f.main_host)
  f.on_disconnect.addCallback(on_disconnect, workers, job_registry)
  
  stratum_listener.MiningSubscription.disconnect_all()
  
  # Reject miners because we don't give a *job :-)
  workers.clear_authorizations() 
  
  return f              

def test_launcher(result, job_registry):
  def run_test():
    log.info("Running performance self-test...")
    for m in (True, False):
      log.info("Generating with midstate: %s" % m)
      log.info("Example getwork:")
      log.info(job_registry.getwork(no_midstate=not m))

      start = time.time()
      n = 10000
      
      for x in range(n):
        job_registry.getwork(no_midstate=not m)
        
      log.info("%d getworks generated in %.03f sec, %d gw/s" % \
           (n, time.time() - start, n / (time.time()-start)))
      
    log.info("Test done")
  reactor.callLater(1, run_test)
  return result

@defer.inlineCallbacks
def main(args):
  if args.pid_file:
    fp = file(args.pid_file, 'w')
    fp.write(str(os.getpid()))
    fp.close()

  log.warning("Trying to connect to Stratum pool at %s:%d" % (args.host, args.port))        
    
  # Connect to Stratum pool
  f = SocketTransportClientFactory(args.host, args.port,
        debug=args.verbose, proxy=None,
        event_handler=client_service.ClientMiningService)
  
  job_registry = jobs.JobRegistry(f, cmd=args.blocknotify_cmd, scrypt_target=args.scrypt_target,
           no_midstate=args.no_midstate, real_target=args.real_target, use_old_target=args.old_target)
  client_service.ClientMiningService.job_registry = job_registry
  client_service.ClientMiningService.reset_timeout()
  
  workers = worker_registry.WorkerRegistry(f)
  f.on_connect.addCallback(on_connect, workers, job_registry)
  f.on_disconnect.addCallback(on_disconnect, workers, job_registry)

  if args.test:
    f.on_connect.addCallback(test_launcher, job_registry)
  
  # Cleanup properly on shutdown
  reactor.addSystemEventTrigger('before', 'shutdown', on_shutdown, f)

  # Block until connect to the pool
  yield f.on_connect

  # thread
  thread = threading.Thread(target=mine, args=[args, job_registry, workers])
  #thread.daemon = True
  thread.start()

import threading
from collections import deque

from hf.load import hf
from hf.load import talkusb
from hf.load.routines import restart

def mine(args, job_registry, workers):
  time.sleep(1)

  # authorize worker
  worker_name     = args.custom_user
  worker_password = args.custom_password
  workers.authorize(worker_name, worker_password)

  # init talkusb
  talkusb.talkusb(hf.INIT, None, 0)

  def printer(msg):
    print(msg)

  # init the test
  test = restart.RestartRoutine(talkusb.talkusb, args.clockrate, printer)

  def get_job(die, core):
    job = job_registry.getwork()
    job['previous block hash'] = hf.reverse_every_four_bytes(job['previous block hash'])
    job['merkle tree root']    = hf.reverse_every_four_bytes(job['merkle tree root'])
    job['bits'] = hf.bebytes_to_int(job['bits'])
    return job

  test.get_job = get_job
  
  valid_nonce_queue = deque([])
  def is_valid_nonce(job, nonce):
    # check nonce
    zerobits, regen_hash_expanded = hf.check_nonce_work(job, nonce)
    if (zerobits >= 39): #if (zerobits >= job_registry.difficulty):
      job['previous block hash'] = hf.reverse_every_four_bytes(job['previous block hash'])
      job['merkle tree root']    = hf.reverse_every_four_bytes(job['merkle tree root'])
      #job['bits'] = hf.int_to_bebytes(job['bits'], 4)
      #job_registry.submit(job, nonce, worker_name)
      valid_nonce_queue.append( (job, nonce, worker_name) )
    return (zerobits >= test.search_difficulty)

  test.is_valid_nonce = is_valid_nonce

  def submit(job_registry):
    while running:
      time.sleep(0.1)
      if len(valid_nonce_queue):
        job, nonce, worker_name = valid_nonce_queue.popleft()
        job_registry.submit(job, nonce, worker_name)

  # submit thread
  submit_thread = threading.Thread(target=submit, args={job_registry})
  #submit_thread.daemon = True
  submit_thread.start()

  def monitor(test):
    while running:
      time.sleep(4)
      test.report_hashrate()
      time.sleep(4)
      test.report_errors()

  # thread
  thread = threading.Thread(target=monitor, args={test})
  #thread.daemon = True
  thread.start()

  # run the test
  rslt = True
  while (rslt and running):
    rslt = test.one_cycle()

  #running = False
  print("All done!")

if __name__ == '__main__':
  main(args)
  reactor.run()
