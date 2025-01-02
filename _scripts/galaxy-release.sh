#!/bin/bash
# Crude script to update the galaxy versions for a new release.
# The collections are always installed from source. There is no Ansible Galaxy release.
# There is no need for changelogs besides the git history as of yet.
# All collections are versioned as one to make it simple.
set -euo pipefail

if [[ ! "${1:-}" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: ${0} major|minor|patch" >&2
    exit 255
fi

cd -- "$(git rev-parse --show-toplevel)/ansible_collections/oszi" || (
    echo "Source 'ansible_collections/oszi' not found." >&2
    exit 2
)

old_version="$(grep -P -o -m1 "^version:\s*['\"]?\K[0-9]+\.[0-9]+\.[0-9]+" environments/galaxy.yml)" || (
    echo "Current version unknown or invalid semver." >&2
    exit 4
)

major="${old_version%%.*}"
minor="${old_version#*.}"
minor="${minor%%.*}"
patch="${old_version##*.}"

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
sed -i -E "s/^(version:)\s+.+\$/\1 \"${new_version}\"/g;\
s/^(\s+['\"]?oszi\.\w+['\"]?:)\s+.+\$/\1 \">=${major}.${minor}\"/g" -- */galaxy.yml

git add -- */galaxy.yml
git commit -n -m "Bump galaxy versions [${new_version}]" -- */galaxy.yml
git tag -s -m "Version ${new_version}" "${new_version}"
