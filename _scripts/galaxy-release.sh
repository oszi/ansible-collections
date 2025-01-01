#!/bin/bash
# Crude script to update the galaxy versions for a new release.
# The collections are always installed from source. There is no Ansible Galaxy release.
# There is no need for changelogs besides the git history as of yet.
# All collections are versioned as one to make it simple.
set -euo pipefail

if [[ ! "${1:-}" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: ${0} major|minor|patch" >&2
    exit 1
fi

cd -- "$(git rev-parse --show-toplevel)/ansible_collections/oszi/"
prev_version="$(grep -E -o -m1 '^version:.*' environments/galaxy.yml | cut -d: -f2)"
prev_version="${prev_version#"${prev_version%%[![:space:]]*}"}"
major="${prev_version%%.*}"
minor="${prev_version#*.}"
minor="${minor%%.*}"
patch="${prev_version##*.}"

if [[ "$1" == "major" ]]; then
    ((++major))
    minor=0
    patch=0
elif [[ "$1" == "minor" ]]; then
    ((++minor))
    patch=0
else
    ((++patch))
fi

new_version="${major}.${minor}.${patch}"
sed -i -E "s/^version: .*/version: ${new_version}/g;\
s/^(\s*['\"]oszi.\w+['\"]:\s*).*/\1\">=${major}.${minor}\"/g" -- */galaxy.yml

git add -- */galaxy.yml
git commit -n -m "Bump galaxy versions [${new_version}]" -- */galaxy.yml
git tag -s -m "Version ${new_version}" "${new_version}"
