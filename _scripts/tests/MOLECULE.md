# Molecule Tests

Molecule tests run the roles of `oszi.general`, `oszi.thirdparty` and `oszi.utils` in rootless Podman
containers with systemd as init. `oszi.environments` is out of scope. Containers get the default
rootless capability set: no `--privileged`, no `CAP_SYS_ADMIN`.

Molecule tests are slow and need podman and network access; agents must not run molecule unless asked.

## Quick start

Requirements: rootless podman with cgroups v2, the venv from `requirements.txt`, and network access to
the image registries, the distribution mirrors and the repositories a scenario installs from.

Scenarios run concurrently with up to 6 workers, detected from two host settings: `fs.inotify.max_user_instances`
allows one worker per 128 instances (raise it to `1024` for the full range), and without the podman transient
store the workers are capped at 2 because `podman exec` throughput does not scale (see below). See the Findings
for technical details.

The output of `test` is always captured and printed only for failed scenarios (running all scenarios produces
over 100k lines); output is also captured when there are multiple workers with any subcommand; stderr is
redirected to stdout to preserve ordering if output is captured.

```bash
# Scenarios of the roles affected since the previous release (opt-in test, see tests README.md)
_scripts/tests/molecule.py
_scripts/tests/molecule.py --ignore-framework # changed roles only, even if framework files changed
_scripts/tests/molecule.py --list

# Scenarios of everything, of given roles or collections, or with other molecule arguments
_scripts/tests/molecule.py --all
_scripts/tests/molecule.py oszi.general.shell oszi.utils.facts
_scripts/tests/molecule.py oszi.general.shell -- test --destroy never

# Molecule directly: build the images from the repository root, then run from a collection directory
ansible-playbook -i localhost, oszi.utils.molecule.build # molecule.py runs this itself
cd ansible_collections/oszi/general
molecule test -s shell --destroy never
molecule login -s shell -h shell-debian
molecule destroy -s shell
```

`molecule reset` removes every container labeled `owner=molecule` and the ephemeral state under
`~/.ansible/tmp/molecule.*`. The message `CRITICAL 'extensions/molecule/default/molecule.yml' glob failed`
is harmless: molecule looks for a `default` scenario to decide about shared state.

Enable podman transient store at the cost of losing all user containers after reboot,
and disable IPv6 if not needed.
```bash
systemctl --user enable podman-clean-transient.service
mkdir -p ~/.config/containers
cat > ~/.config/containers/storage.conf <<EOF
[storage]
driver = "overlay"
transient_store = true

[storage.options.overlay]
mountopt = "nodev,metacopy=on"
EOF
cat > ~/.config/containers/containers.conf <<EOF
[network]
pasta_options = ["--ipv4-only"]
EOF
```

## Layout

```
ansible_collections/oszi/utils/extensions/molecule/
  config.yml       # base config: driver, platforms, ansible

ansible_collections/oszi/{general,thirdparty}/extensions/molecule/
  config.yml       # symlinks to config.yml in utils

ansible_collections/oszi/utils/playbooks/molecule/
  build.yml        # builds the images in containers/; run once before the scenarios
  containers/      # fedora, debian, ubuntu images: systemd + python3 + package bindings + sudo
  prepare.yml      # systemd wait, bootstrap, users_list
  converge.yml     # bootstrap + include_role (derived from the scenario)
  verify.yml       # generic assertions from molecule_verify_* vars

ansible_collections/oszi/{collection}/extensions/molecule/{scenario}/
  molecule.yml     # scenario variables (inventory group_vars)
  prepare.yml      # imports oszi.utils.molecule.prepare, plus test tools
  converge.yml     # imports oszi.utils.molecule.converge or the production playbook
  verify.yml       # imports oszi.utils.molecule.verify, plus specifics

_scripts/tests/molecule.py  # opt-in runner, see tests README.md
```

## How it fits together

Molecule detects a collection from `galaxy.yml` in the current directory, discovers scenarios in
`extensions/molecule/**/molecule.yml` and loads the first base config found: VCS root
`.config/molecule/config.yml`, collection `extensions/molecule/config.yml`, home. The base config is
deep-merged under every scenario's `molecule.yml` (dicts merge recursively, lists are replaced).

The base config sets `prerun: false` (ansible-compat would otherwise try to install the source-only
collections from Galaxy), disables the dependency step, defines the three platforms named
`${MOLECULE_SCENARIO_NAME}-{fedora,debian,ubuntu}` with inventory groups `fedora`/`redhat`, `debian`,
`ubuntu`/`debian` from pre-built images, configures ansible.cfg (pipelining on: so a task costs one
`podman exec`), and sets the inventory defaults such as `ansible_user: root`.

`${VAR}` and `$VAR` in base config and `molecule.yml` are interpolated from molecule's environment
(including `MOLECULE_PROJECT_DIRECTORY`, the collection directory, and `MOLECULE_SCENARIO_NAME`);
a literal dollar sign is `$$`.

### Images

The Containerfiles start from `quay.io/fedora/fedora:latest`, `docker.io/library/debian:stable` and
`docker.io/library/ubuntu:latest` and add systemd, python3, the package manager bindings, `sudo` and
`ca-certificates`. Fedora masks `systemd-oomd` and `systemd-resolved`, which cannot run without extra
capabilities. The package metadata stays in the images and scenarios install from it; the image TTL bounds
its age, and dnf still refreshes repositories past their `metadata_expire`. The OS versions are controlled by
the `MOLECULE_BUILD_{FEDORA,DEBIAN,UBUNTU}_VERSION` environment variables.

The `oszi.utils.molecule.build` playbook builds them as `localhost/molecule_local/oszi/{fedora,debian,ubuntu}`
with `playbooks/molecule/containers` as the build context; `MOLECULE_BUILD_IMAGE_PREFIX` in the environment
replaces the prefix for the playbook and the platforms alike. `molecule.py` runs it once before the scenarios of the
subcommands creating instances (`test`, `create`, `converge`, `prepare`, `check`); run it from the repository root
before invoking molecule directly. An image is rebuilt when it is missing, its Containerfile changed or it is older
than `molecule_build_image_ttl` (`12h`). Expired images and `-e molecule_build_force=true` build without cache and
pull newer base images; otherwise base images are pulled only when missing.

The platforms use the images as `pre_build_image`, so the driver never builds them: the create step fails
with `Can't pull image ...` when an image is missing. Instances kept with `--destroy never` keep their image
until destroyed. Builds from checkouts with different Containerfiles flip the tag between each other,
set a different `MOLECULE_BUILD_IMAGE_PREFIX` to prevent that.

### Shared playbooks (oszi.utils.molecule)

* **build**: Builds the platform images on the controller; see Images above.
* **prepare**: Waits for `systemctl is-system-running` to report `running`
  (`molecule_prepare_systemd_wait: false` skips it), imports `oszi.utils.bootstrap`, creates every user
  in `users_list`, the variable the `users`, `shell`, `dotfiles` and `gnome_users` roles consume, installs
  `molecule_prepare_packages` (test tools, or the packages a rootless role would manage as root) and seeds
  `molecule_prepare_seed_files` (`path`, optional `content`, `mode`, `owner`, `group`; `.repo` files get a
  disabled stub). `molecule_prepare_seed_verify_absent: true` also seeds every `molecule_verify_paths` entry
  with `state: absent`, so an uninstall path has work to do instead of passing on a pristine image.
* **converge**: Imports `oszi.utils.bootstrap`, includes `molecule_converge_roles` (list of `{name, tasks_from}`),
  by default the role named like the scenario up to the first dash in the collection molecule runs from.
  `molecule_become_user` (default `root`) runs the play as another user for rootless scenarios.
* **verify**: Asserts `molecule_verify_paths` (`path`, `state: file|directory|link|absent`, `mode`, `owner`, `group`,
  link `src` as the literal link target, `checksum` as sha256 with or without the `sha256:` prefix, exact
  `content`, `lines` that must each occur), `molecule_verify_commands` (`cmd` in bash with `set -euo pipefail`,
  `user`, exact `stdout` or `stdout_contains`; `! cmd` asserts failure), `molecule_verify_units` (`name`,
  `load` default `loaded` since `systemctl show` reports unknown units as `not-found` with exit code 0,
  `active`, `enabled` as `systemctl show` values) and `molecule_verify_packages` (`present`, `absent`).
  `molecule_verify_role_defaults_file` loads a role's defaults as `molecule_role_defaults`, so expected values
  such as key checksums are read from the role rather than duplicated; defaults templating sibling defaults
  or facts render against the play, so they need those names defined there (facts via a preceding play).
  `molecule_verify_role_vars` (`role`, `tasks_from`, `user`, `that`) includes a role publicly as the given user
  in a play of its own and asserts expressions over its variables, e.g. defaults derived from the effective user or
  exported facts. Paths are stat'ed without following links: a symlinked directory is a `link`, not a `directory`.

### Scenarios

A scenario is `molecule.yml` with `provisioner.inventory.group_vars` (`all`, or `fedora`, `redhat`,
`debian`, `ubuntu`) plus the three stub playbooks importing the shared ones by FQCN. Molecule resolves
`ansible.playbooks` entries as files relative to the scenario directory and skips optional stages whose
file is missing, so FQCNs cannot be configured centrally; the stubs are also where scenarios add their own
plays. Scenario names are `{role}` or `{role}-{variant}`; role names never contain dashes.

`molecule test` runs: destroy, syntax, create, prepare, converge, idempotence, verify, destroy.

## Scenarios in place

Every role of the three collections has a `{role}` scenario; variants cover uninstall paths (`-disabled`),
`update` entrypoints (converge-only test sequence), enabled thirdparty repositories (`-enabled`, vendor network
needed), the upstream repositories of roles defaulting to the distribution package (`-enabled-upstream`, Fedora),
the ssh server, and rootless mode. Heavy by nature: the enabled thirdparty scenarios download vendor packages,
`gnome` installs the full default package set (about 1 GB per platform) to catch packages renamed or dropped
in new distribution releases, `gnome_users` a small dconf set (each setting is a `podman exec`),
and `borgmatic` and `python` need PyPI.

Rootless-tagged roles (`_scripts/galaxy-tags.py -t rootless`) have a `{role}-rootless` scenario running
the role as `tester` via `molecule_become_user`, so `ansible_facts.user_uid` is non-zero and the tilde
paths and `*_manage_packages` defaults apply. `molecule_prepare_packages` installs the packages the role
would manage as root, and `molecule_verify_role_vars` asserts the defaults derived from the user.

Not testable in these containers: firewalld enabled (polkit needs `CAP_SYS_ADMIN`), nested podman
(quadlet and kube services, deploy and pull paths), snaps and `snap update` (snapd exits with 237/KEYRING),
SELinux changes, libvirt daemons, ACME issuance, the CloudFlare API, `localectl`, `wg-quick` interfaces,
and flatpak remotes and apps (bubblewrap).

## Checklist for scenario authors

* Name the scenario `{role}` or `{role}-{variant}`; use `molecule_converge_roles` for other roles or
  `tasks_from` entrypoints, and the production playbook in `converge.yml` when one exists.
* Put variables in `provisioner.inventory.group_vars`; set the cross-role variables the role expects.
* Create users through `users_list`; escape dollar signs as `$$`.
* Never commit key material: generate keys in the scenario `prepare.yml` and keep such tasks `no_log`.
* Use the `molecule_verify_*` lists; add plays to `verify.yml` for anything else and gather facts there
  with `oszi.utils.facts`.
* Assertions must be earned: seed what an uninstall path removes (`molecule_prepare_seed_verify_absent`,
  `molecule_prepare_seed_files`) instead of asserting absence on a pristine image, and let prepare create
  directories with a different mode than the one verify expects, so the role is the one producing the state.
  `ansible.builtin.file` gives that mode to every parent it creates too: create the parents first.
* `fail_msg` of `ansible.builtin.assert` must render to a string; prefix a dict or list with text.
* Negative tests include the role in a `block`/`rescue` and assert `ansible_failed_task.name`; keywords such as
  `check_mode` reach the role's tasks only via `include_role` `apply`. A `fail` after the include guards the rescue.
* `apt remove` keeps conffiles, so a package-removal assertion cannot expect every file of a dpkg package gone.
* Expected values that live in the role (checksums, URLs, versions) come from `molecule_verify_role_defaults_file`
  rather than copies in the scenario.
* `update` entrypoints and `state: latest` belong in a variant whose `scenario.test_sequence` omits
  idempotence.
* Scenarios needing network beyond the distribution mirrors say so in the variant name (`-enabled`).
* Group vars replace lists as a whole: a `debian` list does not extend the `all` list. Build per-distro
  lists from `_common` and `_distro` variables when needed.
* Verify commands run with `pipefail`: `cmd | grep -q` can fail with SIGPIPE; use plain `grep`.
* Only `molecule test` takes `-p`; the single-platform loop is
  `molecule test -s X -p X-debian --destroy never`, then `molecule destroy -s X` before setup changes.
* The images have no `ip` command, so network facts give no `default_ipv4` unless iproute is installed in
  prepare. Other requirements of facts can also be absent.

## Findings

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
* Connecting as root makes Ansible chown its temporary files, so `acl` is not needed for `become_user`.
* Every systemd container consumes several inotify instances of the invoking user. With the common default
  `fs.inotify.max_user_instances = 128`, about ten concurrent instances exhaust the limit: new containers
  exit with status 255 right after create (UNREACHABLE) and dbus-broker fails with EMFILE. The user's desktop
  environment can use up most of the default limit. Raise the sysctl, for example to 1024, before running
  multiple scenarios concurrently.
* Every task is a `podman exec`, and each rootless exec fsyncs the libpod sqlite database about 18 times
  under its exclusive lock (about 0.12s of 0.18s). This caps the host at roughly 9 execs per second across
  all containers and workers while CPU, memory and disk stay idle, so more workers barely help. Podman's
  transient store (`transient_store = true` in a `storage.conf` passed via `CONTAINERS_STORAGE_CONF`, or
  `podman --transient-store`) keeps that database in the runroot tmpfs: about 33 execs per second scaling
  with the workers, images and container layers stay on disk, but the containers are only visible to podman
  processes with the same setting. The driver's create and destroy playbooks also poll `async_status` with
  the default 5s delay. There are only marginal benefits above 6 workers.
* User-wide transient store (`~/.config/containers/storage.conf`) is the simplest way to apply it, as molecule
  has no option for podman global flags (`MOLECULE_PODMAN_EXECUTABLE` must be a bare executable, `reset` runs
  a literal `podman`). Every rootless container then forgets itself on reboot while images, volumes and layers
  persist: quadlets recreate themselves, toolbox containers are lost. Containers created in the other mode
  become invisible, not deleted, until the setting is flipped back. Layers of containers alive at shutdown are
  left behind; enable `podman-clean-transient.service` for the user (`podman system prune --external` once per
  boot, shipped but not preset) to sweep them.
