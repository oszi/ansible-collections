# Ansible Collection - oszi.general

Ansible collection for general, bite-sized, single-purpose roles.

## Collection Rules

* Use assets only from the distribution or contained within the role - with some exceptions.
* For example, python, podman, flatpak and snap install third-party software **after** manual configuration.
* Primary on/off switch: `{role}_disabled: false` - true triggers uninstall or noop.
* Roles that support rootless mode or loop-based rootful mode are tagged as **rootless**.
* Rootful mode or loop-based rootful mode is always the default behavior.
* Roles' galaxy tags reference their corresponding environments.
* General playbooks are also single-purpose, or include a single general role.
* Playbooks always target **all** hosts, environments are responsible for host targeting.
* Thus, only baselinux roles without cross-role variable use may have matching playbooks.
* The **update** playbook includes all "update" entrypoints in general roles.

See the Core Conventions for details.
