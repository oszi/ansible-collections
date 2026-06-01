# Core Conventions

## Best practices

| Practice | Description |
|---|---|
| **Ansible best practices** | Follow official guidelines such as all role variables must be prefixed with the role name, use FQCN for all modules, prefer modules over shell/command... |
| **Idempotency** | Every task must be safely re-runnable. Avoid `command`/`shell` where a module exists; when unavoidable, use `creates`, `removes`, or `changed_when`. |
| **Strict shell scripts** | Use `set -euo pipefail` and `executable: /bin/bash` in `shell` module tasks. Use quoted environment variables to pass values from ansible. |
| **Shell quoting in templates** | Use `\| quote` for strings, `\| to_quoted_tilde_path(...)` for home-dir relative and absolute paths. |
| **Strict permissions** | Set strict `mode`, `owner`, and `group`, unless otherwise required (e.g. rootless). |
| **Become at playbook level** | Set `become` in playbooks, not in roles; do not mix privilege levels. One exception: roles may loop users with `become`, disregarding user facts. |
| **Single-purpose roles** | Each role configures exactly one component. Reject creeping scope. |
| **Opt-in third-party** | Roles managing an external repo must default to disabled and leave the system clean if disabled. |
| **Optional dependencies** | `podman_disabled \| default(false)` or similar cross-role flags must use default defensively. |
| **Cross-role variable use** | When referencing another role's variable (e.g. `users_list`), always guard with `if VAR is defined else []` if the role must work standalone. |
| **Fact namespace** | All fact access must use `ansible_facts.fact_name`, never bare variable injection. |
| **Cross-distro gaps** | Roles must handle both `RedHat` and `Debian` `os_family` for different packages and system paths. |
| **Container environments** | Any role managing systemd units or networking must guard against `virtualization_type` `container` if expected to work in containers (dependencies of `baselinux`). |
| **Role files/templates paths** | Use absolute dest paths as relative for files (.j2 for templates), e.g. `templates/etc/app/app.conf.j2` |
| **argument_specs.yml** | All defaults and entrypoints must have precise argument_specs entries; use yaml anchors for options. |

## Variable naming

| Pattern | Meaning |
|---|---|
| `{role}_disabled: false` | Primary on/off switch for `general` roles; triggers uninstall or noop when `true`. |
| `{role}_enabled: false` | Opt-in on/off switch for `thirdparty` roles; triggers uninstall when `true`. |
| `{role}_{feature}_enabled` | Feature flag, typically derived from `not {role}_disabled`. |
| `{role}_{thing}_list` | List of dicts with a key attribute, produced via `\| nested_dict_to_list('key_attr')` or defined as-is. |
| `{role}_{thing}_pt_{part}` | Component included in `{role}_{thing}` to make partial overrides easy (see `workstation` defaults). |
| `{role}_{thing}_default` | Default value of `{role}_{thing}`; allows merging defaults in the inventory (see `gnome` defaults). |
| `{role}_packages` | List of cross-distro packages; flatten with set_fact in the role. |

## Privilege-aware paths (rootful vs rootless)

**Pre-condition:** `rootless`-tagged roles only.
Root-only roles assert root and use system paths unconditionally.

Defaults must be correct in both rootful and rootless modes without the user setting anything.
Facts as role dependencies guarantee facts exist, and are gathered with the same privilege as the role is run,
because roles do not set `become` as per best practices.

```yaml
# defaults/main.yml pattern
role_install_system: "{{ ansible_facts.user_uid | int == 0 }}"
role_local_bin_path: "{{ local_bin_path | default('/usr/local/bin', true)
  if ansible_facts.user_uid | int == 0
  else ansible_facts.user_dir + '/.local/bin' }}"

# vars/main.yml pattern
role_config_base: "{{ '/etc/component' if ansible_facts.user_uid | int == 0
  else ansible_facts.user_dir + '/.config/component' }}"
```

If tasks are looped per user with `become`, use `ansible.builtin.user` in `check_mode` for valid per-user facts,
applying the **Loop variable pattern** (see `dotfiles` for this approach).

## Systemd scope in handlers

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
  - "{{ ['python3-devel', 'gcc'] if ansible_facts.os_family == 'RedHat' else [] }}"
  - "{{ ['python3-dev', 'build-essential'] if ansible_facts.os_family == 'Debian' else [] }}"
```

## Task structure pattern (tasks/main.yml)

Most `tasks/main.yml` follow a fixed structure: one top-level block tagged with the role name so the role tag does
not apply to dependencies; `include_tasks` orchestration inside; optional inter-role fact exports with `always` tag
(guarantees definition); and a no-op role completed assert at the end to guarantee one task execution per invocation,
otherwise dependencies could be re-run.

Common alternative entrypoints are `tasks/update.yml` and `tasks/{role}.yml`. Alternative entrypoints
must be documented in argument_specs; use yaml anchors for options.

```yaml
- name: Component tasks
  tags: [component]
  block:
    - name: Include installation tasks
      when: component_install_system
      ansible.builtin.include_tasks:
        file: "{{ (not component_disabled) | ternary('install', 'uninstall') }}.yml"

    - name: Include configuration tasks
      when: not component_disabled
      ansible.builtin.include_tasks:
        file: config.yml

    - name: Export component_export_path fact for integrations
      ansible.builtin.set_fact:
        component_export_path: "{{ component_path if not component_disabled else none }}"
        cacheable: true
      tags: [always]

    - name: Component role completed
      ansible.builtin.assert:
        that: true
        quiet: true
```

## Loop variable pattern

Where defaults may legitimately interpolate a loop var, the loop var must be defined as a shape-compatible
placeholder at role load time, because argument_specs validates defaults at entrypoint time.
Common use-case in loop-based user configuration roles, e.g. `dotfiles` and `gnome_users`.

Solution: Wrap the loop var with a placeholder in `vars/main.yml`, loaded at role load time.
Wrapping the loop var - instead of overriding it - prevents "loop variable is already in use" warnings,
and allows extending functionality, e.g. merge role-level defaults into every item.

```yaml
# tasks/main.yml - underscore-prefixed loop_var; comment documents the friendly name
loop_control:
  loop_var: _role_item_var  # use as role_item

# vars/main.yml - friendly name wraps loop var with a placeholder default
role_item: "{{ _role_item_var | default('__PLACEHOLDER__') }}"
```

Placeholder shape must match the expected type - for dicts include all required keys,
and use `combine()` to merge role-level defaults into every item in one expression:

```yaml
# vars/main.yml
role_item: "{{ role_item_default | combine(_role_item_var | default(_role_item_var_placeholder)) }}"
_role_item_var_placeholder:
  dest: "/tmp/__PLACEHOLDER__"
  url: "http://localhost/__PLACEHOLDER__"
```

For values **computed from the loop item** use task-level `vars:` - they evaluate per iteration
and need no placeholder (see `podman_quadlets` for this approach):

```yaml
vars:
  role_item_path: "{{ [role_base_path, role_item.name] | path_join }}"
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

## Facts as role dependencies

Facts are set as role dependencies, making the roles self-contained. Implicit gathering should be disabled
in ansible.cfg and in playbooks, but `oszi.utils.facts` supports implicit gathering and fact caching.
One subset per dependency works best with dependency deduplication.

`!all` and `!min` are implied, unless explicitly specified. Subsets included in `min` should be avoided;
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
