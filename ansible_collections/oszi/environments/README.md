# Ansible Collection - oszi.environments

Ansible collection for personal, high-level environment roles.

* Define role dependencies to **oszi.general** but NOT to **oszi.thirdparty**.
* Each environment role comes with a matching playbook.


### Environments

- **baselinux** - Base for every Linux environment, depends on most roles from **oszi.general**.
- **containerhost** - Baselinux and Podman with systemd-based container services.
- **toolbox** - Baselinux and DevOps tools (CLI). It can be built as a container image.
- **workstation** - Gnome, Flatpak, etc, and workstation-specific tweaks. Recommends Toolbox.
- **macbook** - Dated and unused, basic automation for Macbooks.
