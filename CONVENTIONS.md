# Core Conventions

## Best practices

| Practice | Description |
|---|---|
| **Ansible best practices** | Follow official guidelines enforced by ansible-lint, roles must pass the production profile. Exceptions are allowed case-by-case (noqa comments). |
| **Become at playbook level** | Set `become` in playbooks, not in roles; do not mix privilege levels. Some conventions depend on this. One exception: roles may loop users with `become_user`, invalidating user facts. |
| **argument_specs.yml** | All entrypoints must have precise argument_specs for their defaults; use yaml anchors for options. |
| **Idempotency** | Every task must be safely re-runnable. Avoid `command`/`shell` where a module exists; when unavoidable, use `creates`, `removes`, or `changed_when`. |
| **Check mode** | Every task must support check mode if possible. `command`/`shell` must set `check_mode: false` if they do not change the host. |
| **Strict shell scripts** | Use `set -euo pipefail` and `executable: /bin/bash` in `shell` module tasks. Use quoted environment variables to pass values from ansible. |
| **Shell quoting** | Use `\| quote` for strings, `\| int` for integers, `\| to_quoted_tilde_path(...)` for absolute paths transformed to quoted home-dir relative paths. |
| **Strict permissions** | Set least-privilege `mode`, `owner`, and `group`, except in rootless roles to inherit ansible_user. |
| **Cross-role variable use** | Guard references to other roles' variables if the role must work standalone, e.g. `... if users_list is defined else []` or `podman_disabled \| default(false)`. |
| **Cross-distro gaps** | Roles must handle both `RedHat` and `Debian` `os_family` for different packages and system paths. |
| **Container environments** | Roles managing privileged system settings must guard against `virtualization_type` `container` if expected to work in containers (e.g. dependencies of `baselinux`). |
| **Fact namespace** | All fact access must use `ansible_facts.fact_name`. `inject_facts_as_vars` must be disabled. |
| **Files/templates paths** | Mirror absolute dest paths under `files/` and `templates/`, append `.j2` for templates. |
| **Prefer handlers** | Prefer handlers for triggered tasks, avoid them with complex conditions and in loop-based roles. |
| **Single-purpose roles** | Each role configures exactly one component. Reject creeping scope. |
| **Opt-in third-party** | Roles managing an external repo must default to disabled and leave the system clean if disabled. |
| **Playbook hosts var** | Use a variable for host targeting: `{playbook}_hosts \| default(...)`, or target `all` hosts. |
| **Secrets encryption** | Secrets must be encrypted with ansible-vault, using `_scripts/ansible-vault-id-client`. Vault files must match `*vault.{yml,yaml,json}`. |
| **Secrets exposure** | Tasks handling secrets must set `no_log: true` to prevent credential exposure. |

## Variable naming

| Pattern | Meaning |
|---|---|
| `{role}_disabled: false` | Primary on/off switch for `general` roles; triggers uninstall or noop when `true`. |
| `{role}_enabled: false` | Opt-in on/off switch for `thirdparty` roles; triggers uninstall when `false`. |
| `{role}_{feature}_enabled` | Feature flag, typically derived from `not {role}_disabled`. |
| `{role}_{thing}_list` | List of dicts with a key attribute, produced via `\| nested_dict_to_list('key_attr')` or defined as-is. |
| `{role}_{thing}_pt_{part}` | Component included in `{role}_{thing}` to make partial overrides easy (see `workstation` defaults). |
| `{role}_{thing}_default` | Default value of `{role}_{thing}`; allows merging defaults in the inventory (see `gnome_users`). |
| `{role}_{thing}_path(s)` | Variable for absolute path(s) with (list of) `path` argument_specs type; always use the suffix. |
| `{role}_packages` | List of cross-distro packages; flatten with set_fact in the role. |
| `_{role}_{thing}_result` | Task-registered private variable used only in that task file. |
| `{playbook}_hosts` | Playbook host targeting override used with a default filter; not a role variable. |

## Privilege-aware context (rootful vs rootless)

**Pre-condition:** `rootless`-tagged roles only.
Root-only roles assert root and use system paths unconditionally.

Defaults must be correct in both rootful and rootless modes without the user setting anything.
Facts as role dependencies guarantee facts exist, and are gathered with the same privilege as the role is run,
because roles do not set `become` as per best practices.

```yaml
# defaults/main.yml pattern
rolename_install_system: "{{ ansible_facts.user_uid | int == 0 }}"
rolename_local_bin_path: "{{ local_bin_path | default('/usr/local/bin', true)
  if ansible_facts.user_uid | int == 0
  else ansible_facts.user_dir + '/.local/bin' }}"

# vars/main.yml pattern
rolename_config_base_path: "{{ '/etc/component' if ansible_facts.user_uid | int == 0
  else ansible_facts.user_dir + '/.config/component' }}"
```

If tasks are looped per user with `become` or as root, use `ansible.builtin.user` in `check_mode` for valid per-user facts,
applying the **Loop variable pattern** (see `dotfiles` and `gnome_users` for this approach).

### Systemd scope in tasks

**Pre-condition:** `rootless`-tagged roles only.
Root-only roles use `scope: system` automatically.

```yaml
ansible.builtin.systemd:
  scope: "{{ 'system' if ansible_facts.user_uid | int == 0 else 'user' }}"
  daemon_reload: true
```

## Distribution conditionals

```yaml
# Package name differences
podman_toolbox_package: "{{ (ansible_facts.os_family == 'RedHat') | ternary('toolbox', 'podman-toolbox') }}"

# Platform-specific package lists - set_fact with flatten before use
python_devel_distro_packages:
  - "{{ ['python3-devel', 'gcc', 'redhat-rpm-config'] if ansible_facts.os_family == 'RedHat' else [] }}"
  - "{{ ['python3-dev', 'build-essential'] if ansible_facts.os_family == 'Debian' else [] }}"
  - "python3-virtualenv"
```

## General task structure pattern

Most `tasks/main.yml` in `general` follow a fixed structure (partially applied in other collections):
1. One top-level block tagged with the role name so the role tag does not apply to dependencies.
2. `include_tasks` orchestration. `tasks/{role}.yml` is common if there are no install/uninstall/config tasks to keep main lean.
3. Optional inter-role fact exports with `always` tag (guarantees definition).
4. No-op role completed assert to guarantee one task execution, without it an all-skipped role re-runs as a dependency.

```yaml
- name: Rolename tasks
  tags: [rolename]
  block:
    - name: Include installation tasks
      when: rolename_install_system
      ansible.builtin.include_tasks:
        file: "{{ (not rolename_disabled) | ternary('install', 'uninstall') }}.yml"

    - name: Include configuration tasks
      when: not rolename_disabled
      ansible.builtin.include_tasks:
        file: config.yml

    - name: Export rolename_export_path fact for integrations
      ansible.builtin.set_fact:
        rolename_export_path: "{{ rolename_path if not rolename_disabled else none }}"
        cacheable: true
      tags: [always]

    - name: Rolename role completed
      ansible.builtin.assert:
        that: true
        quiet: true
```

## Update entrypoint pattern

Roles managing packages or container images should have an entrypoint `tasks/update.yml` to update the packages/images
to their latest compatible versions. For example, `package_manager`, `python`, `podman`, `flatpak`, `snap`.

All `update` entrypoints must be included in the `oszi.environments.update` playbook with environment-specific host targeting.

## Loop variable pattern

Where defaults may legitimately interpolate a loop var, the loop var must be defined as a shape-compatible
placeholder at role load time, because argument_specs validates defaults at entrypoint time.
Common use-case in loop-based user configuration roles, e.g. `dotfiles` and `gnome_users`.

Wrap the loop var with a placeholder in `vars/main.yml`, loaded at role load time. Wrapping the loop var -
instead of overriding it - prevents "loop variable is already in use" warnings, and allows extending
functionality, e.g. merge role-level defaults into every item.

```yaml
# tasks/main.yml - underscore-prefixed loop_var; comment documents the friendly name
loop_control:
  loop_var: _rolename_item_var  # use as rolename_item

# vars/main.yml - friendly name wraps loop var with a placeholder default
rolename_item: "{{ _rolename_item_var | default('__PLACEHOLDER__') }}"
```

Placeholder shape must match the expected type - for dicts include all required keys,
and use `combine` to merge role-level defaults into every item in one expression:

```yaml
# vars/main.yml
rolename_item: "{{ rolename_item_default | combine(_rolename_item_var | default(_rolename_item_placeholder)) }}"
_rolename_item_placeholder:
  dest: "/tmp/__PLACEHOLDER__"
  url: "http://localhost/__PLACEHOLDER__"
```

For values **computed from the loop item** use task-level `vars:` - they evaluate per iteration
and need no placeholder (see `podman_quadlets` for this approach):

```yaml
vars:
  rolename_item_path: "{{ [rolename_base_path, rolename_item.name] | path_join }}"
```

## Nested dict to list pattern

List-of-dicts is the preferred structure over dict-of-dicts; argument_specs does not support dict-of-dicts.
The `nested_dict` filters transform between dict and list forms using a key attribute.

**Inventory-side merge pattern** - List is derived in the inventory to combine multiple dicts:
```yaml
users_list: "{{ inventory_users_all | combine(inventory_users_workstations, list_merge='append_rp',
  recursive=true) | oszi.utils.nested_dict_to_list('name') }}"  # key_attribute:name = dict key
```

**Unique list** - Uniqueness can be enforced by a key attribute:
```yaml
loop: "{{ users_list | oszi.utils.unique_nested_list('name') }}"
```

## Facts as role dependencies pattern

Facts must be set as role dependencies, making the roles self-contained. Implicit gathering should be disabled
in ansible.cfg and in playbooks, but `oszi.utils.facts` supports implicit gathering and fact caching.
One subset per dependency works best with dependency deduplication.

`!all` and `!min` are implied, unless explicitly specified. Subsets already covered by `min` should be avoided;
`min` + `virtual` is the default, to limit the number of dependencies.

```yaml
dependencies:
  - role: oszi.utils.facts  # default facts, deduplicated
  - role: oszi.utils.facts
    vars:
      facts_subset: [hardware]
  - role: oszi.utils.facts
    vars:
      facts_subset: [network]
```

## Galaxy tag rules

1. The collection name must be a tag: `general`, `thirdparty`, `environments`, `utils`
2. A mutually exclusive environment tag: `baselinux`, `containers`, `thirdparty`, `toolbox`, `workstation`
3. Rootless XOR root assertion: Roles must either add the `rootless` tag, or assert root privileges.

**Accepted dependencies to assert root privileges:**  
Root assertion requires roles to not set `become` as per best practices (Become at playbook level).
```yaml
# Explicit assertion:
- role: oszi.utils.assert
  vars:
    assert_task_msg: "Assert root privileges"
    assert_that:
      - "ansible_facts.user_uid | int == 0"
# Or via baselinux, which asserts root in its own dependencies:
- role: oszi.environments.baselinux
```

All roles tagged as `rootless` must be included in the `oszi.environments.rootless` playbook.
