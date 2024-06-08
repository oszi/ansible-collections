# Working Examples

### Setup with ansible-galaxy

```bash
ansible-galaxy collection install "git+https://github.com/oszi/ansible_collections.git#/oszi/"
```

\* I prefer to checkout the repository and configure the collections path.

### Running the playbooks

```bash
# cd examples
ansible-playbook --list-tags oszi.environments.workstation
ansible-playbook -K --check --diff oszi.environments.workstation
```

```bash
ansible-playbook --list-tags oszi.general.update
ansible-playbook -K oszi.general.update
```

### Using ansible-vault-id-client

```bash
# Interactively store a GPG encrypted password
../_scripts/ansible-vault-id-client --create --vault-id=example

# Use it with environment variables...
export ANSIBLE_VAULT_IDENTITY_LIST="$(../_scripts/ansible-vault-id-client --check --vault-id=example)"
ansible-vault create inventory/group_vars/workstations/vault.yml

# Or with the CLI arguments
ansible-vault view --vault-id=example@../_scripts/ansible-vault-id-client \
  inventory/group_vars/workstations/vault.yml
```
