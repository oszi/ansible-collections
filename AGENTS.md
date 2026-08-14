# Oszi's Ansible Collections

Personal Ansible collections for Linux workstations and containers.  
Supported distributions: latest stable Fedora, Debian, Ubuntu, and EL when trivial.  
Ansible version: **2.20.0** through latest stable.

## Collections

* **oszi.environments** - High-level environment roles.
* **oszi.general** - General, bite-sized, single-purpose roles.
* **oszi.thirdparty** - Software from third-party sources.
* **oszi.utils** - Ansible plugins and utility roles.

## Where to look for ...

Core Conventions (best practices, variable naming, code patterns): `CONVENTIONS.md`  
Per-collection READMEs: `ansible_collections/oszi/{collection}/README.md`

Playbook location pattern: `ansible_collections/oszi/{collection}/playbooks/{playbook}.yml`  
Role location pattern: `ansible_collections/oszi/{collection}/roles/{role}/`  
Documentation for each role: `meta/argument_specs.yml`

Inventory and user examples: `examples/` and `examples/README.md`  
Utility scripts: `_scripts/` and `_scripts/README.md`

## Releases

**Git tags are the source of truth:** `MAJOR.MINOR.PATCH`  
Current version: `git describe --tags --abbrev=0`  
Changelog: `git show --no-patch MAJOR.MINOR.PATCH`  
Automated by: `_scripts/galaxy-release.sh major|minor|patch`

Tags contain the short git log since the previous tag and which collections were updated.  
Collections can be at different minor/patch versions. Major versions are always in sync.  
Source-only install; no Ansible Galaxy releases.

## Development

**Before making changes, always:**
1. Read `CONVENTIONS.md` for Core Conventions.
2. Read all collections' `README.md` for per-collection rules.

**After making changes:**
* Run tests: `_scripts/run-tests.sh [ansible-lint|ansible-vault|galaxy-tags|python|shellcheck]`  
  There are no molecule or coverage tests yet.
* Never commit changes or create releases yourself.

## Security Model

This project is treated as production for security-sensitive environments.  
Downstream users must not be disclosed; assume the strictest plausible deployment.

* Strict information hygiene in code, documentation, and source control;  
  no deployment-specific rationale, no real identifiers, no secrets.
* Supply chain: pinned refs, checksums, GPG signatures, no `curl | sh`.
* Network exposure and third-party sources are opt-in, not default.
* Consider what a diff might reveal about downstream deployments.

## Code Reviews

**Before reviewing, always:**
1. Read `CONVENTIONS.md` for Core Conventions.
2. Read the affected collections' `README.md` for per-collection rules.
3. Read the affected roles' `meta/argument_specs.yml`.

**Then evaluate:**
* Do changes follow Core Conventions and per-collection rules?
* Do changes comply with the Security Model?
* What production risks could be introduced?
* What edge cases the author might not have anticipated?
* Ignore galaxy version bumps; they are automated.
