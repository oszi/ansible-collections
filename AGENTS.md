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

Inventory and user examples: `examples/`; see `examples/README.md`  
Utility scripts: `_scripts/`; see `_scripts/README.md`  
Test scripts: `_scripts/tests/`; see `_scripts/tests/README.md`

## Releases

**Git tags are the source of truth:** `MAJOR.MINOR.PATCH`  
Latest version: `git describe --tags --abbrev=0 --match='[0-9]*.[0-9]*.[0-9]*'`  
Changelog: `git show --no-patch MAJOR.MINOR.PATCH`  
Automated by: `_scripts/galaxy-release.sh major|minor|patch`

Tags contain the short git log since the previous tag and which collections were updated.  
Updated collection versions are incremented in lockstep; dependencies are pinned.  
Source-only install; no Ansible Galaxy releases.

## Development

**Before making changes, always:**
1. Read `CONVENTIONS.md` for Core Conventions.
2. Read all collections' `README.md` for per-collection rules.
3. Read `_scripts/tests/MOLECULE.md` when working on molecule tests.

**While making changes:**
* Prefer additive, reversible changes; never discard changes you did not create.
* Fix root causes and audit the relevant scope for similar occurrences.
* Write self-contained, present-state prose; comments only explain non-obvious intent or invariants.
* Avoid decorative Unicode; prefer ASCII unless the character is meaningful.

**After making changes:**
* Read `_scripts/tests/README.md` and run tests via `_scripts/run-tests.sh`.  
  Do not run molecule unless asked.
* Never commit changes or create releases yourself.

## Security Model

This project is treated as production for security-sensitive environments.  
Downstream users must not be disclosed; assume the strictest plausible deployment.

* Strict information hygiene in code, documentation, and source control;  
  no deployment-specific rationale, no real identifiers, no secrets.
* Supply chain: pinned refs, checksums, GPG signatures, no `curl | sh`.
* Network exposure and third-party sources are opt-in, not default.
* Inventories are trusted, but input must still be verified.
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
