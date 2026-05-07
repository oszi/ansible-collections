# Examples

The `examples/inventory` directory targets localhost in the workstations group.  
It showcases common role configurations for workstations and container hosts.

Copy, and adapt `activate` and `ansible.cfg` to your requirements.  
See the [_scripts](../_scripts) for utilities and integrations.

## Run some playbooks

```bash
# cd examples
ansible-playbook --list-tags oszi.environments.workstation
ansible-playbook -K --check --diff oszi.environments.workstation
make workstation TAGS=shell,dotfiles
```

```bash
ansible-playbook --list-tags oszi.general.update
ansible-playbook -K oszi.general.update
make update
```

## Use ansible-vault-id-client with ansible-vault

```bash
# Interactively store a GPG encrypted password
../_scripts/ansible-vault-id-client --create --vault-id=inventory/example

# Use it with environment variables...
export ANSIBLE_VAULT_IDENTITY_LIST="$(../_scripts/ansible-vault-id-client --check --vault-id=inventory/example)"
ansible-vault create inventory/group_vars/workstations/vault.yml

# Or with the CLI arguments
ansible-vault view --vault-id=inventory/example@../_scripts/ansible-vault-id-client \
  inventory/group_vars/workstations/vault.yml
```
