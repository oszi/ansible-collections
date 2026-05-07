# Ansible Collection - oszi.thirdparty

Ansible collection for software from third-party sources.

* All third-party sources must be disabled by default via `ROLENAME_enabled` variables.
* Unless enabled, roles must make sure that nothing is installed, not even the repositories.
* With the exception of often conflicting packages, for example, kubectl.
* Include these roles in playbooks and tag them as `thirdparty` for visibility, do not use as dependencies.
* Main task orchestration pattern:
  1. `{{ ansible_facts.os_family | lower }}/{{ ROLENAME_enabled | ternary('install', 'uninstall') }}.yml`
  2. `packages.yml` for installing/uninstalling packages (inline in `main.yml` if simple).
  3. `post-setup.yml` for configuration, shell completions, etc.
* Variables are mixed variants for `rpm` and `deb` repositories.
