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

import sys
import os
import time
import csv
import usb.core
import usb.util
from hf.usb import usbctrl
import subprocess
import traceback
from subprocess import Popen, PIPE
from datetime import datetime
from hf.boardlib import boardlib
import struct
import re

# For testing w/o module
MOC=False

# Customize for your module reference clock
REFERENCE_CLOCK = 25

#TODO: "learn" the current prefix from the scanner as the script runs on the test machine
SERIAL_PREFIX = "PEPPER1-"

#Bus 002 Device 020: ID 297c:0001  
USBID_HF_VID=0x297c
USBID_HF_PID=0x0001
USBID_HFU_PID=0x8001

#Bus 002 Device 021: ID 03eb:2ff6 Atmel Corp. 
USBID_DFU_VID=0x03eb
USBID_DFU_PID=0x2ff6

def randbyteshex(bytecount, source="/dev/urandom"):
    """Return bytecount good pseudorandom bytes as a hex string."""
    src = open(source, "rb")
    thebytes = struct.unpack("B" * bytecount, src.read(bytecount))
    hexstring = "%02x" * bytecount % thebytes
    src.close()
    return hexstring

def reboot_dev():
    if MOC: return
    print("Rebooting module.")
    dev = usbctrl.HFCtrlDevice()
    config = dev.config()
    for module in range(config.modules):
        return dev.reboot(module,0x0000)

def read_serial(serial_in="FAIL"):
    print("Reading serial number from module.")
    if MOC:
        return serial_in
    dev = usbctrl.HFCtrlDevice()
    config = dev.config()
    for module in range(config.modules):
        return dev.serial(module).pretty_str()

# TODO: replace w/ the Python fn
def write_serial(serial_number):
    if MOC: return
    # TODO: sanity check input for "HF:0x32n:FH"
    try:
        result = subprocess.check_output(['./writeserial', serial_number])
    except subprocess.CalledProcessError as e:
        traceback.print_exc(file=sys.stdout)
        print(e)
        print(result)
        throw
    return

def wait_for_hf():
    if MOC: return

    dev = usb.core.find(idVendor=USBID_HF_VID, idProduct=USBID_HF_PID)
    if dev is None:
        print("Please connect the module in HashFast Miner Mode to the test machine.")
    while usb.core.find(idVendor=USBID_HF_VID, idProduct=USBID_HF_PID) == None:
        time.sleep(1)
    time.sleep(3)

def get_module_id():
    module_id = sys.stdin.readline().rstrip()

    # If they have to manually key in the last digits of the serial
    while len(module_id) < 4:
        module_id = "0" + module_id
    if not module_id.startswith(SERIAL_PREFIX):
        module_id = SERIAL_PREFIX + module_id
    # TODO: check board ID for format or at least sanity
    return module_id

# TODO: replace w/ the Python fn
def write_die_settings(hash_clock, voltage):
    if MOC: return
    pass_fail_args=["./hcm",
                    "--write-die-settings",
                    "*:%d@%d" % (voltage, hash_clock),
                    "--ref-clock",
                    "%s" % REFERENCE_CLOCK]
    result = "FAIL"
    try:
        result = subprocess.check_output(pass_fail_args, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        # This happens when there's a "libusb_bulk_transfer() failed while receiving: Input/Output Error" from hcm
        traceback.print_exc(file=sys.stdout)
        print(e)
        result = "FAIL"

    return result

def hfload_test(hash_clock, cycles):
    import random
    import sys
    import time

    from hf.load import hf
    from hf.load import talkusb
    from hf.load.routines import simple

    if MOC:
        expected_hash_rate = hash_clock * 1000000000 * 0.745
        #return expected_hash_rate * 1.1 # success
        return expected_hash_rate * 0.75 # fail

    talkusb.talkusb(hf.INIT, None, 0);

    def printmsg(msg):
        print(msg)

    # pass in "lambda *a, **k: None" for print fn
    HRT = simple.SimpleRoutine(talkusb.talkusb, hash_clock, printmsg, deterministic=True)
    if not HRT.n_cycles(cycles):
        print("ALERT: test failed to complete.  Measured hash rate so far is '%d'." % HRT.get_hashrate())
        return 0

    return HRT.get_hashrate()


def automatic_test(hash_clock, voltage, cycles, firmware):


    if not MOC and firmware != "NONE":
        print("Connect module and wait for firmware load to complete.")
        subprocess.check_output(['./firmware_update.py', '--firmware', firmware])
        print("Firmware loaded.")
        time.sleep (10)
    else:
        print("Connect module.")
        wait_for_hf()
        print("Firmware load skipped.")
        reboot_dev()

    wait_for_hf()

    print("Initializing die settings...")
    write_die_settings(hash_clock, voltage)

    print("Waiting for HashFast module.")

    wait_for_hf()

    print("Running automatic test...")
    serial="NONE"
    hash_rate = hfload_test(hash_clock, cycles)
    expected_hash_rate = hash_clock * 1000000000 * 0.745
    min_pass_hash_rate = expected_hash_rate * 0.9
    assert (min_pass_hash_rate > 1000000000)

    test_result = "FAIL"
    if hash_rate > min_pass_hash_rate:
        test_result = "PASS"
    else:
        percent = int(100 * (hash_rate / expected_hash_rate))
        print("")
        print("FAILED: Hash rate is %d percent of expected value. Please run test again with voltage set to %d" % (percent, voltage + 10))

    print("")
    print("****************************************")
    print("expected hash rate: %s" % expected_hash_rate)
    print("min pass hash rate: %s" % min_pass_hash_rate)
    print("hash rate:          %s" % hash_rate)
    print("result: %s" % test_result)
    print("****************************************")
    print("")

    return (test_result, hash_rate)

def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description='HashFast Automatic Test.')
    parser.add_argument('--module-id', action='store', default='PROMPT',
                       help='specify the module ID (board label).  Else, prompt for it.')
    parser.add_argument('--serial', action='store', default='GENERATE',
                       help='Use this serial number for the module.')
    parser.add_argument('--hash-clock', action='store', default='800',
                       help='Speed to qualify the module at.')
    parser.add_argument('--voltage', action='store', default='940',
                       help='Default voltage to test module at.')
    parser.add_argument('--cycles', action='store', default='5000',
                       help='Cycles to run test for.')
    parser.add_argument('--firmware', action='store', default='NONE',
                       help='path to firmware image to load.')
    parser.add_argument('--moc', action='store_true',
                       help='Test w/o an actual module.')
    args = parser.parse_args()

    global MOC
    MOC = args.moc

    print("module_id: '%s'" % args.module_id)
    print("serial: '%s'" % args.serial)
    print("hash_clock: '%s'" % args.hash_clock)
    print("voltage: '%s'" % args.voltage)

    try:
        print("Beginning Board Load and Test")
        if (args.module_id == 'PROMPT'):
            print("Please scan the label to begin.")
            module_id=get_module_id()
            print("module_id: %s" % args.module_id)
        else:
            module_id=args.module_id

        result = automatic_test(int(args.hash_clock), int(args.voltage), int(args.cycles), args.firmware)
        serial = "NONE"
        if (result[0] == "PASS"):
            if (args.serial == 'GENERATE'):
                serial_rand = randbyteshex(16)
                serial = "HF::" + serial_rand + "::FH"
                print("generated serial: %s" % args.serial)
            else:
                serial = args.serial

            print('Writing serial: "%s".' % serial)
            reboot_dev()

            wait_for_hf()

            write_serial(serial)

            wait_for_hf()
            serial_back=read_serial(serial)
            if serial_back != serial:
                print("Error: failed to read back serial correctly.")
                print("          Serial is '%s'." % serial)
                print("Read back serial is '%s'." % serial_back)
                raise Exception("Error: failed to read back serial correctly.")

        test_data = {'serial': serial,
                     'module_id': module_id,
                     'test_result': result[0],
                     'hash_rate': int(float(result[1])),
                     'hash_clock': int(args.hash_clock),
                     'voltage': int(args.voltage),
                     'cycles': int(args.cycles),
                     'firmware': args.firmware,
                    }
        datawriter = boardlib.BoardData('/home/netcom/test_results')
        datawriter.Store(test_data, 'Pepper')

        print("Board Test Completed")
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print(e)
        print("Board Test had an error.  Please retry.")
        exit(1)
    except KeyboardInterrupt:
        print("")
        print("Board Test Cancelled.  Exiting.")
        exit(1)

    print("Disconnect HF device from system.")

    while usb.core.find(idVendor=USBID_HF_VID, idProduct=USBID_HF_PID) != None:
        time.sleep (1)

    print("Test Completed.")
    print("")
    print("**** Result: %s" % result[0])
    if result[1] == 0:
        print("************ TEST FAILED TO COMPLETE.  Check rig for thermal cooling, wiring, and power issues.")
    print("")

    exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])

