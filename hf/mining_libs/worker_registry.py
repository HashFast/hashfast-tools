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

import time

import stratum.logger
log = stratum.logger.get_logger('proxy')

class WorkerRegistry(object):
    def __init__(self, f):
        self.f = f # Factory of Stratum client
        self.clear_authorizations()
        
    def clear_authorizations(self):
        self.authorized = []
        self.unauthorized = []
        self.last_failure = 0
    
    def _on_authorized(self, result, worker_name):
        if result == True:
            self.authorized.append(worker_name)
        else:
            self.unauthorized.append(worker_name)
        return result
    
    def _on_failure(self, failure, worker_name):
        log.exception("Cannot authorize worker '%s'" % worker_name)
        self.last_failure = time.time()
                        
    def authorize(self, worker_name, password):
        if worker_name in self.authorized:
            return True
            
        if worker_name in self.unauthorized and time.time() - self.last_failure < 60:
            # Prevent flooding of mining.authorize() requests 
            log.warning("Authentication of worker '%s' with password '%s' failed, next attempt in few seconds..." % \
                    (worker_name, password))
            return False
        
        d = self.f.rpc('mining.authorize', [worker_name, password])
        d.addCallback(self._on_authorized, worker_name)
        d.addErrback(self._on_failure, worker_name)
        return d
         
    def is_authorized(self, worker_name):
        return (worker_name in self.authorized)
    
    def is_unauthorized(self, worker_name):
        return (worker_name in self.unauthorized)  
