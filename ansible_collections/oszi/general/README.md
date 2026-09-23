# Ansible Collection - oszi.general

Ansible collection for general, bite-sized, single-purpose roles.

## Collection Rules

* Use assets only from the distribution or contained within the role - with some exceptions.
* For example, python, podman, flatpak and snap install third-party software **after** manual configuration.
* Primary on/off switch: `{role}_disabled: false` - true triggers uninstall or noop.
* Roles' galaxy tags reference their corresponding environments, and whether they are rootless-compatible.
* General playbooks are also single-purpose, or include a single general role.
* Playbooks always target **all** hosts, environments are responsible for host targeting.
* Thus, only **baselinux** roles without cross-role variable use may have matching playbooks.

See the Core Conventions for details.
