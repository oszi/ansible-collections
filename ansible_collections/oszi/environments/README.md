# Ansible Collection - oszi.environments

Ansible collection for personal, high-level environment roles.

* Define dependencies to other environment roles and from **oszi.general**.
* But manually import roles from **oszi.thirdparty** in playbooks.
* Each environment role comes with a matching playbook.


### Environments

- **baselinux** - Base for every Linux environment, depends on most roles from oszi.general.
- **containerhost** - Baselinux and podman with systemd-based container services.
- **toolbox** - DevOps tools, including third-party. It can be built as a container image.
- **workstation** - Toolbox and containerhost with Gnome and workstation-specific tweaks.
- **macbook** - Dated and unused, basic automation for Macbooks.
