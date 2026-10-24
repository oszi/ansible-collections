# Ansible Collection - oszi.thirdparty

Ansible collection for software from third-party sources.

## Collection Rules

* All third-party sources must be disabled by default via the `{role}_enabled` opt-in on/off switch.
* Unless enabled, roles must make sure that nothing is installed, not even the repositories.
* With the exception of often conflicting packages, for example, kubectl.
* Repository and file URLs must be configurable and verified to support mirrors.
* Include these roles in playbooks and tag them as `thirdparty` for visibility, do not use as dependencies.

## Collection Guidelines

* Main task orchestration pattern:
  1. `{{ ansible_facts.os_family | lower }}/{{ {role}_enabled | ternary('install', 'uninstall') }}.yml`
  2. `packages.yml` for installing/uninstalling packages (inline in `main.yml` if simple).
  3. `post-setup.yml` when `{role}_enabled` is true for configuration, shell completions, etc.
* Defaults for third-party repository roles:
  * `{role}_{rpm,deb}_baseurl` for repository URLs - support mirrors.
  * `{role}_{rpm,deb}_gpgkey_url` for GPG keys to download - do not bundle.
  * `{role}_{rpm,deb}_gpgkey_checksum` for GPG key checksums in the format of `get_url`.
  * `{role}_deb_gpgkey_armored` for .asc/.gpg extension in `gpgkey_path`.
* Vars for third-party repository roles:
  * `{role}_{rpm,deb}_{repo_path,gpgkey_path}` for managed paths.
  * `{role}_{rpm,deb}_absent_paths` for vendor/legacy paths to remove in `install` and `uninstall` tasks.
  * `{role}_rpm_repo_args` for `yum_repository` args incorporating `baseurl` and path vars.
  * `{role}_deb_repo` for Deb822 .sources incorporating `baseurl` and path vars.
* Notable special use-cases:
  * See `google_chrome_manage_repository` in `oszi.thirdparty.google_chrome`.
  * See `tailscale_upstream_enabled` and `post-setup.yml` in `oszi.thirdparty.tailscale`.
  * See multiple signing keys in `oszi.thirdparty.opentofu`.
