# _scripts

Scripts to facilitate ansible deployments and source control.

If you're using a git submodule, symlink what you need in a _scripts directory.

* [ansible-ssh](../ansible_collections/oszi/environments/roles/toolbox/files/bin/ansible-ssh)  
SSH into a host in an ansible inventory with all configured arguments.

* [ansible-vault-id-client](../ansible_collections/oszi/environments/roles/toolbox/files/bin/ansible-vault-id-client)  
Script to use as "vault id" for GPG encrypted vault passwords.

* [galaxy-release.sh](galaxy-release.sh)  
Update the galaxy versions for a new release.

* [git-init.sh](git-init.sh)  
Initialize git hooks and git submodules after cloning.

* [git-pre-commit.sh](git-pre-commit.sh)  
Pre-commit hook to protect sensitive files and to run linters.

* [git-reset.sh](git-reset.sh)  
Verify and reset the repository to a remote branch - master by default.

* [git-verify.sh](git-verify.sh)  
Verify the signatures of all git branches and tags.
