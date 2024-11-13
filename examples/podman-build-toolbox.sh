#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$(realpath -- "$0")")"

base_image="quay.io/fedora/fedora:latest"
image="quay.io/oszi/toolbox:latest"
container="toolbox-${RANDOM}"
set -x

podman create -t --name="$container" "$base_image" bash
trap 'podman rm -ifv "$container"' EXIT
podman start "$container"
podman exec "$container" dnf -y install python3-libdnf5  # Fedora 41+

ansible-playbook -c podman -i "${container}," oszi.environments.toolbox

podman exec "$container" sh -c "rm -rf /root/.cache/* /var/cache/ansible/* /var/cache/dnf/*"
podman commit -c 'LABEL com.github.containers.toolbox="true"' "$container" "$image"
