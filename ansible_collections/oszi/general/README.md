# Ansible Collection - oszi.general

Ansible collection for general, bite-sized, single-purpose roles.

* Use assets only from the distribution or contained within the role - with some exceptions.
* For example, python, podman, flatpak and snap install third-party software **after** manual configuration.
* Primary on/off switch: `ROLENAME_disabled: false` - true triggers uninstall or noop.
* General playbooks also serve a single-purpose and always target **all** hosts.
* Roles supporting **rootless** mode (or loop-based rootful mode) are tagged as rootless.
* Set galaxy tags for corresponding environments. Use `_scripts/tests/galaxy-tags.py` to test tags.
