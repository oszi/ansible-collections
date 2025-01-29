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

cd -- "$(git rev-parse --show-toplevel)/ansible_collections/oszi" || {
    echo "Source 'ansible_collections/oszi' not found." >&2
    exit 2
}

old_version="$(grep -P -o -m1 "^version:\s*['\"]?\K[0-9]+\.[0-9]+\.[0-9]+" environments/galaxy.yml)" || {
    echo "Current version unknown or invalid semver." >&2
    exit 4
}

changes="$(git log --no-merges --pretty=format:"* %s" "${old_version}...HEAD")"
[[ -n "$changes" ]] || {
    echo "No commits found since the last version." >&2
    exit 6
}

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
new_version_spec="==${new_version}"

sed -i -E "s/^(version:).*\$/\1 \"${new_version}\"/g;\
s/^(\s+['\"]?oszi\.\w+['\"]?:).*\$/\1 \"${new_version_spec}\"/g" -- */galaxy.yml

git add -- */galaxy.yml

git commit -n -m "Bump galaxy versions [${new_version}]" -- */galaxy.yml || {
    git reset --quiet HEAD -- */galaxy.yml
    git checkout --quiet HEAD -- */galaxy.yml
    exit 8
}

git tag -s -m "Version ${new_version}" -m "${changes}" "${new_version}" || {
    git reset --quiet --soft HEAD~1
    git checkout --quiet HEAD -- */galaxy.yml
    exit 8
}
