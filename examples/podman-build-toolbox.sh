#!/bin/bash
cd "$(dirname "$(realpath "$0")")"
set -euo pipefail

base_image="registry.fedoraproject.org/fedora:latest"
image="toolbox:latest"
container="toolbox-${RANDOM}"
set -x

podman create -t --name="$container" "$base_image" bash
trap "podman rm -ifv "$container"" EXIT
podman start "$container"

ansible-playbook -i "${container}," -c podman -e is_container=true \
  oszi.environments.toolbox

podman exec "$container" sh -c "rm -rf /root/.cache/* /var/cache/ansible/* /var/cache/dnf/*"
podman commit -c "LABEL com.github.containers.toolbox=\"true\"" "$container" "$image"
