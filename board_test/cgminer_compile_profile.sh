#!/bin/bash

DEFAULT_CGMINER_DIR="/home/hashfast/cgminer.hf"

DEFAULT_TIME="600"
DEFAULT_SPEED="600"
DEFAULT_WALLET="DONATE_realmine"
DEFAULT_POOL="stratum+tcp://stratum.mining.eligius.st:3334"

CGMINER_DIR=${HF_CGMINER_DIR:-$DEFAULT_CGMINER_DIR}

(cd $CGMINER_DIR && CFLAGS="-pg -O2 -Wall -march=native" LDFLAGS="-pg" ./configure --enable-hashfast && make)

CGMINER="$CGMINER_DIR/cgminer"

TIME=${1:-$DEFAULT_TIME}
SPEED=${2:-$DEFAULT_SPEED}
WALLET=${3:-$DEFAULT_WALLET}
POOL=${4:-$DEFAULT_POOL}

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

echo "CGMINER is \"$CGMINER\"."

ARGS="--verbose -o ${POOL} -u ${WALLET} -p x -l 9 --hfa-hash-clock $SPEED --hfa-ntime-roll 45"
echo "ARGS are \"$ARGS\"."

echo "STARTING CGMINER"
$CGMINER ${ARGS} 2> miner.stderr &
sleep $TIME

kill $! 2> /dev/null

FILENAME="cgminer_$(date +%s)"

echo "DATE: $(date)" > "${FILENAME}.txt"
echo "TIME: $TIME seconds" >> "${FILENAME}.txt"
echo "COMMIT: " >> "${FILENAME}.txt"
echo "NOTES: " >> "${FILENAME}.txt"
echo "==========================" >> "${FILENAME}.txt"
echo "==========================" >> "${FILENAME}.txt"

gprof $CGMINER >> "${FILENAME}.txt"
