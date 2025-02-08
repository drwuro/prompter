#!/bin/sh


# mount USB drive

sleep 2
if [ -e "/dev/sda" ]; then
  mount /dev/sda1 /mnt/usb
fi

sleep 7


# run prompter directly from USB drive if available (allows newer versions)

if [ -e "/mnt/usb/prompter" ]; then
  cd /mnt/usb/prompter
else
  cd /home/zeha/prompter

fi


echo "\n\n----------------------------\n\n"
LD_LIBRARY_PATH=/usr/local/lib python3 src/prompter.py
