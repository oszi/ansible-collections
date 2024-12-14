# shellcheck shell=sh

_borg_export_pass() {
    borg_config="${1:-/etc/borgmatic/config.yaml}"

    if sudo grep -Pzo '(?s)\brepositor(ies:\s*((\n\s*-\N+)+|\[[^\]]+\])|y:\N+)\n?' "$borg_config"; then
        BORG_PASSPHRASE="$(sudo grep -E '^\s*encryption_passphrase:' "$borg_config" | awk -F': ' '{print $2}')"
        export BORG_PASSPHRASE
    else
        echo "Invalid borg config - ${borg_config}" >&2
        false
    fi
}

alias borg-export-pass='_borg_export_pass'
alias borg1='borg --remote-path=borg1'
