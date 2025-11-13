# Ansible Collection - oszi.environments

Ansible collection for personal, high-level environment roles.

* Define role dependencies to **oszi.general** but NOT to **oszi.thirdparty**.
* Each environment role comes with a targeted, matching playbook.
* Include roles from **oszi.thirdparty** in the playbooks.

## Environments

- **baselinux** - Base for every Linux environment, depends on most roles from **oszi.general**.
- **containerhost** - Baselinux and Podman with systemd-based container services.
- **toolbox** - Baselinux and DevOps tools (CLI). It can be built as a container image.
- **workstation** - Baselinux, Gnome, Flatpak, etc, and workstation-specific tweaks.  
  The workstation playbook also includes **containerhost** and **toolbox**.
- **rootless** - A playbook of roles that support rootless mode - from dotfiles to containers.
