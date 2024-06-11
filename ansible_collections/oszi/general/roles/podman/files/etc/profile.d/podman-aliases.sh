alias p='podman'
alias pexec-priv='podman exec -itu root --privileged'
alias pexec='podman exec -it'
alias pgc='podman ps -aqf status=exited -f status=created | xargs -r podman rm'
alias pgcimg='podman images -qf dangling=true | xargs -r podman rmi'
alias pimg='podman images'
alias pinsp-ip='podman inspect -f {{.NetworkSettings.IPAddress}} --type=container'
alias pinsp='podman inspect'
alias plogs='podman logs'
alias pps='podman ps -a --format="table {{.Names}} {{.Image}} {{.Command}} {{.Status}}"'
alias prun='podman run --rm -ite TERM'
alias pxargs='xargs -n1 -r podman'

alias chcon-container='chcon -Rt container_file_t'

pcleanup() {
  pgc -fv && pgcimg
}

pimggrep() {
  podman images --format='{{.Repository}} {{.Tag}}' | grep "$@" | awk '{if ($2!="<none>") print $1":"$2}'
}

ppsgrep() {
  podman ps -a --format='{{.Names}} {{.Image}} {{.Status}}' | grep "$@" | awk '{print $1}'
}

prmgrep() {
  ppsgrep "$@" | xargs -r podman rm --force --volumes
}

pstatsgrep() {
  ppsgrep "$@" | xargs -r podman stats --no-stream
}

ppullgrep() {
  pimggrep "$@" | xargs -L1 -P3 -r podman pull
}

ppushgrep() {
  pimggrep "$@" | xargs -n1 -r podman push
}
