#!/bin/bash
set -euo pipefail
cd "$(dirname "$(realpath "$0")")/.."
exec < /dev/tty

echo -n "Run ansible-lint? [y/N]" >&2
read answer
if echo "${answer}" | grep -iq '^Y'; then
  ansible-lint oszi/ examples/inventory/
fi
