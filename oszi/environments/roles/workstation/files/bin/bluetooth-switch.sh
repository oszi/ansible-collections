#!/bin/bash
# Connect to or disconnect from the selected bluetooth device.
set -euo pipefail

paired_devices=`bluetoothctl paired-devices` || paired_devices=`bluetoothctl devices Paired`

choice=`echo "$paired_devices" \
  | awk '{"bluetoothctl info "$2" | grep -iqE \"^\\\s*connected:\\\s*yes\" && echo [+] || echo [-]" | getline $1; print $0}' \
  | sort -k 3 | fzf --no-multi --no-sort --tac`

cmd=`echo "$choice" | grep -q '^\\[+\\]' && echo disconnect || echo connect`
device=`echo "$choice" | awk '{print $2}'`

bluetoothctl "$cmd" "$device"
