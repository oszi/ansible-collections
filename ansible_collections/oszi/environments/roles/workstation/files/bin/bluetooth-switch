#!/bin/bash
# Connect to or disconnect from the selected bluetooth device.
set -euo pipefail

if ! (command -v bluetoothctl && command -v fzf) >/dev/null 2>&1; then
    echo "bluetoothctl or fzf not found!" >&2
    exit 1
fi

paired_devices=$(
    while read -r device; do
        bluetoothctl info "${device:0:17}" | grep -Eiq '^\s*connected:\s*yes' \
            && echo -n '[+] ' || echo -n '[-] '
        echo "$device"
    done < <(bluetoothctl devices Paired | grep -Eio '\b([0-9A-F]{2}:){5}[0-9A-F]{2}\b.*$')
)

if [ "$paired_devices" == "" ]; then
    echo "No paired devices found! Is bluetooth disabled?" >&2
    exit 1
fi

choice="$(echo "$paired_devices" | sort -k 3 | fzf --no-multi --no-sort --tac)"
cmd="$(echo "$choice" | grep -q '^\[+\]' && echo disconnect || echo connect)"
device="$(echo "$choice" | awk '{print $2}')"

bluetoothctl "$cmd" "$device"
