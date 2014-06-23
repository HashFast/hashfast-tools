#!/usr/bin/env python

# Fix: This script is unforgiving to people who make mistakes.  Should have a final
#      "This is what I got, is it okay?" question and let people make corrections.

import sys
import os
import time
import csv
import usb.core
import usb.util
import subprocess
import traceback
from subprocess import Popen, PIPE
import struct
import re

#TODO: "learn" the current prefix from the scanner as the script runs on the test machine
SERIAL_PREFIX = "CUSTOMIZEME-"

#Bus 002 Device 020: ID 297c:0001  
USBID_HF_VID=0x297c
USBID_HF_PID=0x0001
USBID_HFU_PID=0x8001

#Bus 002 Device 021: ID 03eb:2ff6 Atmel Corp. 
USBID_DFU_VID=0x03eb
USBID_DFU_PID=0x2ff6
UC_PART='at32uc3b0512'

# HashFast Boot Loader, in HEX format
HFU_HEX_FILE='uc3_loader_dfu_update.hex'
#HFU_HFU_FILE='uc3_loader_dfu_update.hfu'

# HashFast uC hex file for legacy DFU mode loads
#UC_HEX_FILE='uc3.cropped.hex'

# HashFast uH HFU hex file for use with hfupdate
UC_HFU_FILE='uc3.cropped.hfu'

def randbyteshex(bytecount, source="/dev/urandom"):
    """Return bytecount good pseudorandom bytes as a hex string."""
    src = open(source, "r")
    thebytes = struct.unpack("B" * bytecount, src.read(bytecount))
    hexstring = "%02x" * bytecount % thebytes
    src.close()
    return hexstring

def read_serial():
    print ("Reading serial number from module.")
    try:
        result = subprocess.check_output(['../utils/readserial'])
        result = result.rstrip()
    except subprocess.CalledProcessError as e:
        traceback.print_exc(file=sys.stdout)
        print e
        print result
        throw
    # TODO: sanity check input for "HF:0x32n:FH"
    print ("Got back this serial: '%s'" % result)
    return result

def write_serial(serial_number):
    # TODO: sanity check input for "HF:0x32n:FH"
    try:
        result = subprocess.check_output(['../utils/writeserial', serial_number])
    except subprocess.CalledProcessError as e:
        traceback.print_exc(file=sys.stdout)
        print e
        print result
        throw
    return

def load_firmware_dfu(hex_file):
    # TODO: check permissions, give udev advice if bad perms
    print ("Initiating firmware load for device in DFU state.")

    # apparently the below precaution was a false alarm
    #if UC_PART == 'at32uc3b0256':
        # Do NOT do the 'erase' on a module, only on EVK
        # On module, it erases boot loader too

    subprocess.check_call(['dfu-programmer', UC_PART, 'erase'])

    subprocess.check_call(['dfu-programmer', UC_PART, 'flash', '--suppress-bootloader-mem', hex_file])
    subprocess.check_call(["dfu-programmer", UC_PART, 'reset'])
    # TODO: verify here that HF device present
    # TODO: check permissions, give udev advice if bad perms
    return

def load_firmware_hfu(hex_file):
    # TODO: check permissions, give udev advice if bad perms
    print ("Initiating firmware load for device in HFU state.")

    subprocess.check_call(['../utils/hfupdate', '-m0', hex_file, '-r'])
    # TODO: verify here that HF device present
    # TODO: check permissions, give udev advice if bad perms
    return

def wait_for_hf():
    dev = usb.core.find(idVendor=USBID_HF_VID, idProduct=USBID_HF_PID)
    if dev is None:
        print ("Please connect the module in HashFast Miner Mode to the test machine.")
    while (usb.core.find(idVendor=USBID_HF_VID, idProduct=USBID_HF_PID) == None):
        # TODO: if they plug in a progammed HF module, bail.
        time.sleep (1)
    print
    print ("HashFast Module in Miner Mode found.")
    print

# Wait for the HashFast Boot Loader to appear
def wait_for_hfu():
    dev = usb.core.find(idVendor=USBID_HF_VID, idProduct=USBID_HFU_PID)
    if dev is None:
        print ("Please connect the module in HashFast Boot Loader Mode to the test machine.")
    while (usb.core.find(idVendor=USBID_HF_VID, idProduct=USBID_HFU_PID) == None):
        # TODO: if they plug in a progammed HF module, bail.
        time.sleep (1)
    print
    print ("HashFast Module Boot Loader found.")
    print

def wait_for_dfu_or_hf_bl():
    dev = usb.core.find(idVendor=USBID_DFU_VID, idProduct=USBID_DFU_PID)
    if dev is None:
        print ("Please connect the module in DFU Mode of HashFast Boot Loader Mode to the test machine.")
    while usb.core.find(idVendor=USBID_DFU_VID, idProduct=USBID_DFU_PID) == None:
        time.sleep (1)
        if usb.core.find(idVendor=USBID_HF_VID, idProduct=USBID_HFU_PID) != None:
            print
            print ("HashFast Module in HashFast Boot Loader mode found.  Programming...")
            print
            return False
    print
    print ("HashFast Module in DFU mode found.  Programming...")
    print
    return True

def get_board_id():
    board_id = sys.stdin.readline().rstrip()

    # If they have to manually key in the last digits of the serial
    while (len(board_id) < 4):
        board_id = "0" + board_id
    if not board_id.startswith(SERIAL_PREFIX):
        board_id = SERIAL_PREFIX + board_id
    # TODO: check board ID for format or at least sanity
    return board_id

def board_load_and_test():

    print ("Please scan board under test to begin.")
    board_id=get_board_id()
    if wait_for_dfu_or_hf_bl():
        # Found DFU
        time.sleep(2)
        load_firmware_dfu(HFU_HEX_FILE)
        time.sleep(3)

    wait_for_hfu()
    time.sleep(2)
    load_firmware_hfu(UC_HFU_FILE)

    time.sleep(3)
    wait_for_hf()

    serial_rand = randbyteshex(16)
    serial = "HF::" + serial_rand + "::FH"
    print ('Writing serial: "%s".' % serial)
    time.sleep(3)

    write_serial(serial)
    serial_back=read_serial()
    if (serial_back != serial):
        print ("Error: failed to read back serial correctly.")
        raise Exception("Error: failed to read back serial correctly.")

    print
    print ("***MICROCONTROLLER TESTS PASS -- GOOD BOARD")
    print ("***NOW RUN CHIP TESTS")
    print

    print "Run realmine.sh at 675 MHz and check to see if the current is between"
    print "31 - 39, and is stable."
    print

    print "Enter the ./realmine.sh current: "
    rm_current = sys.stdin.readline().rstrip()

    print "Enter the ./realmine.sh hardware errors: "
    rm_hw_errors = sys.stdin.readline().rstrip()

    print "Enter any notes about this module: "
    notes = sys.stdin.readline().rstrip()
    print

    with open('serial_number_db_rev1_1a.csv', 'ab') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([serial, board_id, rm_hw_errors, rm_current, notes])

    print
    print ("***BOARD LOAD AND TEST COMPLETE")
    print

    return

if __name__ == "__main__":
    if (not os.path.isfile(HFU_HEX_FILE)):
        print ("HFU HEX file not found.  Cannot run.  Expected: %s" % HFU_HEX_FILE)
        exit(1)
    if (not os.path.isfile(UC_HFU_FILE)):
        print ("uC HFU file not found.  Cannot run.  Expected: %s" % UC_HFU_FILE)
        exit(1)

    while (1):
        print
        try:
            print "Beginning Board Load and Test"
            board_load_and_test()
            print "Board Load and Test Completed"
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            print e
            print "Board Test had an error.  Please retry."
        except KeyboardInterrupt:
            print
            print "Board Test Cancelled.  Exiting."
            exit(1)
        time.sleep(2)

