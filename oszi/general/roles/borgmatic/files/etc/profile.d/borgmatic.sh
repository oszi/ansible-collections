_borg_export_pass() {
  config="${1:-/etc/borgmatic/config.yaml}"
  sudo grep -Pzo '(?s)\brepositor(ies:\s*((\n\s*-\N+)+|\[[^\]]+\])|y:\N+)\n?' "$config" 2>/dev/null \
  && export BORG_PASSPHRASE=$(sudo grep -E '^\s*encryption_passphrase:' "$config" | awk -F': ' '{print $2}') \
  || echo "Invalid borgmatic config - ${config}" >&2
}

alias borg-export-pass='_borg_export_pass'
alias borg1='borg --remote-path=borg1'
