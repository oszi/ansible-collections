# Ansible Collection - oszi.environments

Ansible collection for personal, high-level environment roles.

## Environments

* **baselinux** - Base for every Linux environment, depends on most roles from **oszi.general**.
* **containerhost** - Baselinux and Podman with systemd-based container services.
* **toolbox** - Baselinux and DevOps tools (CLI). It can be built as a container image.
* **workstation** - Baselinux, Gnome, Flatpak, etc, and workstation-specific tweaks.  
  The workstation playbook also includes **containerhost** and **toolbox**.
* **rootless** - A playbook of all roles that support rootless mode - from dotfiles to containers.

## Collection Rules

* Each environment role comes with a targeted, matching playbook.
* Define role dependencies to **oszi.general** but NOT to **oszi.thirdparty**.
* Include roles from **oszi.thirdparty** in the playbooks, tagged as **thirdparty**.
* Environment roles may implement various tasks that do not warrant a general role.
