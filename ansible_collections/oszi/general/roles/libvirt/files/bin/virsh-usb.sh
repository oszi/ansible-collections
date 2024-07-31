#!/bin/bash
set -euo pipefail

if [[ $# -ne 2 ]] || ! [[ "$1" =~ ^(at|de)tach$ ]]; then
  echo "Usage: $0 attach|detach device-pattern" >&2
  exit 1
fi

command="$1"
pattern="$2"

if ! (command -v virsh && command -v fzf && command -v xmllint) >/dev/null 2>&1; then
  echo "virsh|fzf|xmllint not found" >&2
  exit 1
fi

domains="$(sudo virsh list --all --name | sort)"  # (sudo before fzf)
if [ -z "$domains" ]; then
  echo "virsh list --all returned empty" >&2
  exit 1
fi

device=$(
  for device in /sys/bus/usb/devices/*; do
    if grep -is -- "$pattern" "${device}/manufacturer" "${device}/product" >/dev/null 2>&1; then
      echo "${device} $(cat "${device}/manufacturer") $(cat "${device}/product")"
    fi
  done | fzf --no-multi --no-sort | awk '{print $1}'
)

vendor_id="$(cat "${device}/idVendor")"
product_id="$(cat "${device}/idProduct")"
device_xpath="//domain/devices/hostdev/source/vendor[@id='0x${vendor_id}']/following-sibling::product[@id='0x${product_id}']"

function virsh_command() {
  local command="$1"
  local domain="$2"

  cat <<EOF | sudo virsh "${command}-device" "$domain" /dev/stdin --current
<hostdev mode="subsystem" type="usb" managed="yes">
  <source>
    <vendor id="0x${vendor_id}"/>
    <product id="0x${product_id}"/>
  </source>
</hostdev>
EOF
}

for domain in ${domains[@]}; do
  if sudo virsh dumpxml "$domain" | xmllint --xpath "$device_xpath" - >/dev/null 2>&1; then
    echo -n "Detach ${vendor_id}:${product_id} from ${domain}? [Y/n]" >&2
    read answer
    if echo "$answer" | grep -iqv '^N'; then
      virsh_command detach "$domain"
    fi
  fi
done

if [[ "$command" == attach ]]; then
  domain="$(echo "$domains" | fzf --no-multi --no-sort --tac)"

  if grep -q Yubi "${device}/manufacturer"; then
    if systemctl status pcscd >/dev/null 2>&1; then
      sudo systemctl stop pcscd ||:
    else
      killall -q gpg-agent ssh-agent ||:
    fi
  fi

  echo "Attaching ${vendor_id}:${product_id} to ${domain}" >&2
  virsh_command attach "$domain"
fi
