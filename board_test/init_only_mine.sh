#!/bin/bash

CGMINER="/home/hashfast/cgminer.hf/cgminer"
WALLET="DONATE_initmine"

lsusb -d 297c:001 >& /dev/null
if [ $? == 0 ]; then
  BUS=`lsusb -d 297c:0001 | cut -d' ' -f 2`
  DEV=`lsusb -d 297c:0001 | cut -d' ' -f 4 | tr   ':' ' '`
  echo BUS is $BUS
  echo DEV is $DEV
  if [ ! -w /dev/bus/usb/$BUS/$DEV ]; then
      echo "HF device not rw mode.  chmodding."
      sudo chmod 666 /dev/bus/usb/$BUS/$DEV
      sleep 3
  fi
else
  echo "HF device not found.  Continuing anyhow."
  echo "HF device not found.  Continuing anyhow."
  echo "HF device not found.  Continuing anyhow."
  echo
  sleep 3
fi

ARGS="--text-only --debug --verbose -o stratum+tcp://stratum.mining.eligius.st:3334 -u ${WALLET} -p x -l 9 --hfa-hash-clock 125 --hfa-init-only"
echo "ARGS are \"$ARGS\"."
$CGMINER ${ARGS} 2> miner.stderr

