# Oszi's Ansible Collections

Personal Ansible collections for Linux workstations and containers.  
Supported distributions: latest stable Fedora, Debian, Ubuntu, and EL for some roles.  
Ansible version: **2.20.0** through latest stable.

For scripts, see `_scripts/` + `_scripts/README.md`  
For tests, see `_scripts/tests/` + `_scripts/tests/README.md`  
For getting started with inventories, see `examples/` + `examples/README.md`

## Location Patterns

Playbook location pattern: `ansible_collections/oszi/{collection}/playbooks/{playbook}.yml`  
Role location pattern: `ansible_collections/oszi/{collection}/roles/{role}/`  
Always consult `meta/argument_specs.yml` for role variables.

## Versioning & Releases

**Git tags are the source of truth**: `MAJOR.MINOR.PATCH`  
Current version: `git describe --tags --abbrev=0`  
Changelog: `git show --no-patch MAJOR.MINOR.PATCH`  
Automated by: `_scripts/galaxy-release.sh major|minor|patch`

Tags contain the short git log since the previous tag and which collections were updated.  
Collections can be at different minor/patch versions. Major versions are always in sync.  
Source-only install; no Ansible Galaxy releases.

## Code Reviews

* Do changes follow Core Conventions and per-collection rules?
* What production and security risks could be introduced?
* What edge cases the author might not have anticipated?
* Ignore galaxy version bumps; they are automated.

## Per-collection Rules

@ansible_collections/oszi/environments/README.md  
@ansible_collections/oszi/general/README.md  
@ansible_collections/oszi/thirdparty/README.md  
@ansible_collections/oszi/utils/README.md

## Core Conventions

@CONVENTIONS.md
