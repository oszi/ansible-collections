# Documentation for AI Agents

Personal Ansible collections for Linux workstations and containers.  
Supported distributions: latest stable Fedora, Debian, Ubuntu, and EL for some roles.  
Minimum Ansible version: **2.18.0** (Support up to the latest.)  
For getting started with inventories, see `examples/`.

## Collection Hierarchy

* **oszi.utils** - Plugins + utility roles (no host changes).
* **oszi.general** - General, single-purpose roles (depends on oszi.utils).
* **oszi.thirdparty** - Opt-in third-party source roles (depends on oszi.utils).
* **oszi.environments** - Composite environment roles (depends on oszi.general + oszi.utils).

### Collection READMEs (authoritative per-collection rules)

@ansible_collections/oszi/utils/README.md  
@ansible_collections/oszi/general/README.md  
@ansible_collections/oszi/thirdparty/README.md  
@ansible_collections/oszi/environments/README.md

### Roles

Role location pattern: `ansible_collections/oszi/{collection}/roles/{role}/`  
Always consult `meta/argument_specs.yml` for role variables.

## Versioning & Releases

**Git tags are the source of truth**: `MAJOR.MINOR.PATCH`  
Latest version: `git describe --tags --abbrev=0 origin/master`  
Changelog: `git show --no-patch MAJOR.MINOR.PATCH`

Tags contain the short git log since the previous tag and which collections were updated.  
Collections can be at different minor/patch versions. Major versions are always in sync.  
Source-only install; no Ansible Galaxy releases.

## Scripts, Testing & Linting

@_scripts/README.md  
@_scripts/tests/README.md

All tests must pass before a release.

## Code Reviews

* Always review the actual changes in the commits.
* Do changes follow Core Conventions?
* What could go wrong in production?
* Could anything introduce vulnerabilities or expand attack surface?
* Could anything expose secrets or sensitive files?
* Do not mention version bumps in reviews.

## Core Conventions

@CONVENTIONS.md
