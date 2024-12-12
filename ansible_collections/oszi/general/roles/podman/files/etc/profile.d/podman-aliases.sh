# shellcheck shell=sh disable=SC2154 # referenced but not assigned
[ "${PS1-}" ] || return

alias podman-images="podman image list --sort=repository --format='{{if eq .Tag \"<none>\"}}{{println (join .RepoDigests \"\n\")}}{{else}}{{.Repository}}:{{println .Tag}}{{end}}'"
alias podman-containers="podman container list --all --sort=names --format='table {{.Names}} {{.Image}} {{.Ports}} {{.Status}}'"
alias podman-ipaddress="podman inspect --type=container --format='{{range \$key, \$val := .NetworkSettings.Networks}}{{\$val.IPAddress}}{{end}}'"

if command -v chcon >/dev/null 2>&1; then
    alias chcon-container='chcon -Rt container_file_t'
fi
