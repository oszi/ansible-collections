# Ansible Collection - oszi.thirdparty

Ansible collection for software from third-party sources.

* All third-party sources must be disabled by default via ROLENAME_enabled variables.
* Unless manually enabled, roles must make sure the software is not installed.
* Include these roles in playbooks and tag them as `third-party`.
