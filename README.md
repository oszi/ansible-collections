# Oszi's Ansible Collections

Personal collections of ansible roles and playbooks for Linux workstations and containers.  
Supported distributions include the latest stable Fedora, Debian, Ubuntu.  
Most roles also work with the latest RedHat family distributions after some tweaking.  
See the examples and role defaults for basic documentation...

### Collections

* [oszi.environments](ansible_collections/oszi/environments) -
High-level environment roles.
* [oszi.general](ansible_collections/oszi/general) -
General, bite-sized, single-purpose roles.
* [oszi.thirdparty](ansible_collections/oszi/thirdparty) -
Software from third-party sources.

### First-time setup

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

See the examples for configuring ansible. Symlink what you need from _scripts.

Commits are signed by [AFDE0AB3943D1FB3](https://oszi.dev/oszi.dev.asc)
