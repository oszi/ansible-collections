#!/bin/bash
# Script to update the collection versions and git tags for a new release.
# This repository uses lock-step semantic versioning with version pinning:
# - Only the affected collections are updated in a release.
# - Minor versions may be skipped but they are always sequential.
# - Major versions are always in sync for every collection.
# - Git tags are strictly incremental and contain all relevant release information.
# The collections are always installed from source; there is no Ansible Galaxy release.
# There are no galaxy changelogs - use the git history instead.
set -euo pipefail

if [[ ! "${1:-}" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: ${0} major|minor|patch" >&2
    exit 2
fi

SEVERITY="$1"
NAMESPACE="oszi"

cd -- "$(git rev-parse --show-toplevel)/ansible_collections/${NAMESPACE}" || {
    echo "Source 'ansible_collections/${NAMESPACE}' not found." >&2
    exit 1
}

# Get the closest tag on the current branch. Supports backport branches.
latest_version="$(git describe --tags --abbrev=0 | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$')" || {
    echo "Latest version unknown." >&2
    exit 4
}

change_log="$(git log --no-merges --pretty=format:"* %s" "${latest_version}..HEAD")"
[[ -n "$change_log" ]] || {
    echo "There are no commits since the latest version." >&2
    exit 4
}

declare -a collections_all
declare -a collections_affected

# shellcheck disable=SC2011 # find instead of ls
read -r -a collections_all -d '' < <(ls -- */galaxy.yml | xargs dirname --) ||:

get_affected_collections() {
    if [[ "$SEVERITY" == "major" ]]; then
        printf '%s\n' "${collections_all[@]}"
        return 0
    fi

    # List changed files since the latest version and staged dependency updates in */galaxy.yml
    (git diff-tree -r --no-commit-id --name-only "${latest_version}..HEAD" \
            && git diff --cached --name-only --diff-filter=ACM -- '*/galaxy.yml') \
        | grep -E -o "^ansible_collections/${NAMESPACE}/[^/]+" \
        | sort -u | xargs -r basename -a --
}

read -r -a collections_affected -d '' < <(get_affected_collections) ||:

major="${latest_version%%.*}"
minor="${latest_version#*.}"
minor="${minor%%.*}"
patch="${latest_version##*.}"

if [[ "$SEVERITY" == "major" ]]; then
    ((++major))
    minor=0
    patch=0
elif [[ "$SEVERITY" == "minor" ]]; then
    ((++minor))
    patch=0
else
    ((++patch))
fi

new_version="${major}.${minor}.${patch}"
new_version_spec="==${new_version}"

[[ "${#collections_affected[@]}" -gt 0 ]] || {
    git commit -n --allow-empty -m "Update repository version [${new_version}]" || exit 6
    git tag -s -m "Version ${new_version}" -m "${change_log}" -m "Collections updated: -" "${new_version}" || {
        git reset --quiet --soft HEAD~1
        exit 6
    }

    echo "There are no affected collections. Not updating galaxy versions." >&2
    exit 0
}

# Update pinned dependencies - affects dependent collections...
for collection_item in "${collections_affected[@]}"; do
    sed -i -E "s/^(\s+['\"]?${NAMESPACE}\.${collection_item}['\"]?:).*\$/\1 \"${new_version_spec}\"/g" -- */galaxy.yml
done

git add -- */galaxy.yml
read -r -a collections_affected -d '' < <(get_affected_collections) ||:

for collection_item in "${collections_affected[@]}"; do
    sed -i -E "s/^(version:).*\$/\1 \"${new_version}\"/g" -- "${collection_item}/galaxy.yml"
done

git add -- */galaxy.yml

git commit -n -m "Update galaxy versions [${new_version}]" -- */galaxy.yml || {
    git reset --quiet HEAD -- */galaxy.yml
    git checkout --quiet HEAD -- */galaxy.yml
    exit 8
}

change_log_collections="Collections updated:

$(printf "* ${NAMESPACE}."'%s\n' "${collections_affected[@]}")"

git tag -s -m "Version ${new_version}" -m "${change_log}" -m "${change_log_collections}" "${new_version}" || {
    git reset --quiet --soft HEAD~1
    git checkout --quiet HEAD -- */galaxy.yml
    exit 8
}
