# _scripts

Scripts to facilitate ansible deployments and source control.

* **[ansible-ssh](../ansible_collections/oszi/environments/roles/toolbox/files/bin/ansible-ssh)**
  `[--help] [SSH_ARGS ...] [host [command ...]]`  
  SSH into a host in an ansible inventory with all configured arguments.
* **[ansible-vault-id-client](../ansible_collections/oszi/environments/roles/toolbox/files/bin/ansible-vault-id-client)**
  `[--check|--create] [--vault-id=VAULT_ID]`  
  Script to use as "vault id" for GPG encrypted vault passwords.
* **[galaxy-release.sh](galaxy-release.sh)** `major|minor|patch`  
  Update the galaxy versions and git tag a new release.
* **[galaxy-tags.py](galaxy-tags.py)** `[--json] [-t TAG1,TAG2]`  
  List ansible roles grouped by galaxy tags.
* **[git-init.sh](git-init.sh)**  
  Initialize git hooks and git submodules after cloning.
* **[git-pre-commit.sh](git-pre-commit.sh)**  
  Pre-commit hook to protect sensitive files.
* **[git-reset.sh](git-reset.sh)** `[-f|--force] [[REMOTE(origin)] BRANCH(master)]`  
  Verify and reset the repository to a remote branch.
* **[git-verify.sh](git-verify.sh)**  
  Verify the signatures of all git branches and tags.
* **[run-tests.sh](run-tests.sh)** `[-h|--help] | [TESTS ...]`  
  Run test scripts in [_scripts/tests](tests) (e.g., ansible-lint or shellcheck).
* **[_ansible.mk](_ansible.mk)** `localhost workstation update versions ... playbooks/* oszi.*`  
  `[VERBOSE=y] [CHECK=y] [LIMIT=HOST] [TAGS=TAG1,TAG2] [SKIP_TAGS=TAG1,TAG2]`  
  Makefile fragment for a common ansible interface. See the [examples](../examples).
* **[_scripts.mk](_scripts.mk)** `venv update-collections tests reset clean`  
  `[COLLECTIONS=path] [SCRIPTS=path] [VENV=path]`  
  Makefile fragment for venv and scripts integration.

If collections is a git submodule, symlink what you need in a _scripts directory.  
All scripts (except galaxy*) support parent repositories.
