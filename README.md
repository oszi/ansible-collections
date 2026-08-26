# Oszi's Ansible Collections

Personal collections of Ansible roles and playbooks for Linux workstations and containers.  
Supported distributions are the latest stable Fedora, Debian and Ubuntu.  
See the examples and role argument_specs for basic documentation.

## Collections

* [oszi.environments](ansible_collections/oszi/environments) -
  High-level environment roles.
* [oszi.general](ansible_collections/oszi/general) -
  General, bite-sized, single-purpose roles.
* [oszi.thirdparty](ansible_collections/oszi/thirdparty) -
  Software from third-party sources.
* [oszi.utils](ansible_collections/oszi/utils) -
  Ansible plugins and utility roles.

## First-time setup

**Install with ansible-galaxy from source:**

```bash
ansible-galaxy collection install \
  "git+https://github.com/oszi/ansible-collections.git#/ansible_collections/oszi/" \
  -p ansible/collections
```

**Install as a git submodule:**

```bash
git submodule add "https://github.com/oszi/ansible-collections.git" ansible/collections
```

See the [examples](examples) for setting up an ansible inventory.

## Development

* [Core Conventions](CONVENTIONS.md) - Best practices and patterns.
* [AGENTS.md](AGENTS.md) - Agentic context, also useful for developers.
* [\_scripts](_scripts) - Tests, utilities and integrations.

## Release policy

This repository uses lockstep semantic versioning. Git tags are the source of truth.  
The collections are always installed from source; there is no Ansible Galaxy release.  
Obsolete backwards-compatibility support may be dropped at any time.

Commits are signed by [AFDE0AB3943D1FB3](https://oszi.dev/oszi.dev.asc)
