# Molecule Tests

Molecule tests run the roles of `oszi.general`, `oszi.thirdparty` and `oszi.utils` in rootless Podman
containers with systemd as PID 1. `oszi.environments` is out of scope. Containers get the default
rootless capability set: no `--privileged`, no `CAP_SYS_ADMIN`.

Molecule runs are slow and need podman plus network access, so agents must not start them on their own.

## Quick start

Requirements: rootless podman with cgroups v2, the venv from `requirements.txt`, and network access to
the image registries, the distribution mirrors and the repositories a scenario installs from.

Every systemd container consumes several inotify instances of the invoking user. With the Fedora default
`fs.inotify.max_user_instances = 128`, about ten concurrent instances exhaust the limit: new containers
exit with status 255 right after create (UNREACHABLE) and dbus-broker fails with EMFILE. Raise the sysctl
(for example to 1024) before running many scenarios concurrently.

```bash
# Scenarios of the roles affected since the previous release (opt-in test, see README.md)
_scripts/run-tests.sh molecule
_scripts/tests/molecule.py --list
_scripts/tests/molecule.py --ignore-framework   # changed roles only, even if shared framework files changed

# Scenarios of given roles or collections, of everything, or with other molecule arguments
_scripts/tests/molecule.py oszi.general.shell oszi.utils.facts
_scripts/tests/molecule.py --all
_scripts/tests/molecule.py oszi.general.shell -- test --destroy never

# Molecule directly, always from a collection directory
cd ansible_collections/oszi/general
molecule test -s shell --destroy never    # keeps the instances; also skips the initial destroy
molecule login -s shell -h shell-debian
molecule destroy -s shell

# Refresh the base images (podman build --pull=newer), from the repository root
ansible-playbook -i localhost, oszi.utils.molecule.images -e molecule_images_pull=newer
```

`molecule reset` removes every container labeled `owner=molecule` and the ephemeral state under
`~/.ansible/tmp/molecule.*`. The message `CRITICAL 'extensions/molecule/default/molecule.yml' glob failed`
is harmless: molecule looks for a `default` scenario to decide about shared state.

## Layout

```
ansible_collections/oszi/utils/extensions/molecule/config.yml   # base config: driver, platforms, ansible
ansible_collections/oszi/{general,thirdparty}/extensions/molecule/config.yml   # symlinks to the above
ansible_collections/oszi/utils/playbooks/molecule/
  images.yml                                        # builds localhost/oszi/molecule-{fedora,debian,ubuntu}
  prepare.yml                                       # systemd wait, package cache, users_list
  converge.yml                                      # bootstrap + include_role (derived from the scenario)
  verify.yml                                        # generic assertions from molecule_verify_* vars
  files/Containerfile.{fedora,debian,ubuntu}        # systemd + python3 + package bindings + sudo
ansible_collections/oszi/{collection}/extensions/molecule/{scenario}/
  molecule.yml                                      # scenario variables (inventory group_vars)
  prepare.yml                                       # imports oszi.utils.molecule.prepare, plus test tools
  converge.yml                                      # imports oszi.utils.molecule.converge or the production playbook
  verify.yml                                        # imports oszi.utils.molecule.verify, plus specifics
_scripts/tests/molecule.py                          # opt-in runner, see README.md
```

## How it fits together

Molecule detects a collection from `galaxy.yml` in the current directory, discovers scenarios in
`extensions/molecule/**/molecule.yml` and loads the first base config found: VCS root
`.config/molecule/config.yml`, collection `extensions/molecule/config.yml`, home. The base config is
deep-merged under every scenario's `molecule.yml` (dicts merge recursively, lists are replaced).

The base config sets `prerun: false` (ansible-compat would otherwise try to install the source-only
collections from Galaxy), builds the images in the dependency step, defines the three platforms named
`${MOLECULE_SCENARIO_NAME}-{fedora,debian,ubuntu}` with inventory groups `fedora`/`redhat`, `debian`,
`ubuntu`/`debian`, points `ANSIBLE_CONFIG` at the repository `ansible.cfg` (its relative `collections_path`
resolves against the file), and sets the inventory defaults `ansible_user: root` and
`bootstrap_package_update_cache: true`.

`${VAR}` and `$VAR` in base config and `molecule.yml` are interpolated from molecule's environment
(including `MOLECULE_PROJECT_DIRECTORY`, the collection directory, and `MOLECULE_SCENARIO_NAME`); a literal
dollar sign is `$$`.

### Images

The Containerfiles start from `quay.io/fedora/fedora:latest`, `docker.io/library/debian:stable-slim` and
`docker.io/library/ubuntu:latest` and add systemd, python3, the package manager bindings, `sudo` and
`ca-certificates`. Fedora masks `systemd-oomd` and `systemd-resolved`, which cannot run without extra
capabilities. The apt lists are removed and dated back so the apt module refreshes them on first use.
Images are rebuilt by every run with cached layers; base images are pulled only when missing.

### Shared playbooks (oszi.utils)

* **prepare**: waits for `systemctl is-system-running` to report `running`
  (`molecule_prepare_systemd_wait: false` skips it), imports `oszi.utils.bootstrap` (package cache) and
  creates every user in `users_list`, the variable the `users`, `shell`, `dotfiles` and `gnome_users`
  roles consume.
* **converge**: imports `oszi.utils.bootstrap`, then includes `molecule_converge_roles` (list of
  `{name, tasks_from}`), by default the role named like the scenario up to the first dash in the collection
  molecule runs from. `molecule_become_user` (default `root`) runs the play as another user for rootless
  scenarios.
* **verify**: asserts `molecule_verify_paths` (`path`, `state: file|directory|link|absent`, `mode`,
  `owner`, `group`, link `src`), `molecule_verify_commands` (`cmd` in bash with `set -euo pipefail`,
  `user`, exact `stdout` or `stdout_contains`), `molecule_verify_units` (`name`, `load`, `active`, `enabled`
  as `systemctl show` values) and `molecule_verify_packages` (`present`, `absent`).
* **images**: see above.

These playbooks alter or inspect molecule instances only; the oszi.utils README rule about not altering
hosts should gain that exception.

### Scenarios

A scenario is `molecule.yml` with `provisioner.inventory.group_vars` (`all`, or `fedora`, `redhat`,
`debian`, `ubuntu`) plus the three stub playbooks importing the shared ones by FQCN. Molecule resolves
`ansible.playbooks` entries as files relative to the scenario directory and skips optional stages whose
file is missing, so FQCNs cannot be configured centrally; the stubs are also where scenarios add their own
plays. Scenario names are `{role}` or `{role}-{variant}`; role names never contain dashes.

`molecule test` runs: dependency, destroy, syntax, create, prepare, converge, idempotence (second converge
with zero changes), verify, destroy.

## Findings (verified 2026-10-30)

* Rootless default capabilities: `chown, dac_override, fowner, fsetid, kill, setgid, setuid, setpcap,
  net_bind_service, sys_chroot, setfcap`. systemd as PID 1 works with them: Debian and Ubuntu boot to
  `running`, Fedora once oomd and resolved are masked; logind, journald, dbus and `user@UID.service` work.
  `CAP_NET_ADMIN` and `CAP_NET_RAW` can be added per scenario by redefining `platforms` with
  `capabilities`; `CAP_SYS_ADMIN` is out, which also rules out polkit and systemd sandboxing such as
  `DynamicUser` (`226/NAMESPACE`).
* `ansible_facts.virtualization_type` is `podman` on Debian and Ubuntu images but `container` on Fedora
  images, which set `ENV container=oci`; unprivileged users cannot read `/proc/1/environ` and the fallback
  `/run/systemd/container` yields `oci`. The roles guard on `virtualization_tech_guest`, which contains
  `container` for every user and image.
* Molecule: `provisioner.inventory.group_vars` feeds inventory variables (the `ansible:` section has no
  inventory key) and play `vars` outrank them; `dependency.env` is ignored for the shell dependency;
  `--destroy never` also skips the initial destroy; the podman driver cannot use a shared Dockerfile,
  hence the prebuilt images.
* The apt module's `cache_valid_time` compares the mtime of `/var/lib/apt/lists`; the dnf module rejects
  `cache_valid_time`, so `bootstrap_apt_cache_valid_time` stays in the `debian` group.
* Connecting as root makes Ansible chown its temporary files, so `acl` is not needed for `become_user`.

## Scenarios in place

Every role of the three collections has a `{role}` scenario; variants cover uninstall paths (`-disabled`),
`update` entrypoints (converge-only test sequence), enabled thirdparty repositories (`-enabled`, vendor
network needed), the ssh server, and rootless mode. Heavy by nature: the enabled thirdparty scenarios
download vendor packages, `gnome` uses a reduced package list, `gnome_users` a small dconf set (each
setting is a `podman exec`), and `borgmatic` and `python` need PyPI.

Rootless-tagged roles (`_scripts/galaxy-tags.py -t rootless`) have a `{role}-rootless` scenario running
the role as `tester` via `molecule_become_user`, so `ansible_facts.user_uid` is non-zero and the tilde
paths and `*_manage_packages` defaults apply. Their prepare installs the packages the role would manage
as root and sets `bootstrap_package_update_cache: false` for the converge.

Not testable in these containers: firewalld enabled (polkit needs `CAP_SYS_ADMIN`), nested podman
(quadlet and kube services, deploy and pull paths), snaps and `snap update` (snapd exits with
237/KEYRING), SELinux changes, libvirt daemons, ACME issuance, the CloudFlare API, `localectl`, `wg-quick`
interfaces, and flatpak remotes and apps (bubblewrap).

## Checklist for scenario authors

* Name the scenario `{role}` or `{role}-{variant}`; use `molecule_converge_roles` for other roles or
  `tasks_from` entrypoints, and the production playbook in `converge.yml` when one exists.
* Put variables in `provisioner.inventory.group_vars`; set the cross-role variables the role expects.
* Create users through `users_list`; escape dollar signs as `$$`.
* Never commit key material: generate keys in the scenario `prepare.yml` and keep such tasks `no_log`.
* Use the `molecule_verify_*` lists; add plays to `verify.yml` for anything else and gather facts there
  with `oszi.utils.facts`.
* `update` entrypoints and `state: latest` belong in a variant whose `scenario.test_sequence` omits
  idempotence.
* Scenarios needing network beyond the distribution mirrors say so in the variant name (`-enabled`).
* Group_vars replace lists as a whole: a `debian` list does not extend the `all` list. Build per-distro
  lists from `_common` and `_distro` variables when needed.
* Verify commands run with `pipefail`: `cmd | grep -q` can fail with SIGPIPE; use plain `grep`.
* Only `molecule test` takes `-p`; the single-platform loop is
  `molecule test -s X -p X-debian --destroy never`, then `molecule destroy -s X` before setup changes.
* The images have no `ip` command, so network facts give no `default_ipv4` unless iproute is installed in
  prepare.
