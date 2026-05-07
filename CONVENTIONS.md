# Core Conventions

## Best practices

| Practice | Description |
|---|---|
| **Ansible best practices** | Follow official guidelines such as all role variables must be prefixed with the role name, use FQCN for all modules, prefer modules over shell/command... |
| **Idempotency** | Every task must be safely re-runnable. Avoid `command`/`shell` where a module exists; when unavoidable, use `creates`, `removes`, or `changed_when`. |
| **Strict shell scripts** | Use `set -euo pipefail` and `executable: /bin/bash` in `shell` module tasks. Use quoted environment variables to pass values from ansible. |
| **Shell quoting in templates** | Use `\| quote` for strings, `\| to_quoted_tilde_path(...)` for home-dir relative paths. |
| **Strict permissions** | Set strict `mode`, `owner`, and `group`, unless otherwise required (e.g. rootless). |
| **Become at playbook level** | Set `become` in playbooks, not in roles, unless a task is looped per user. |
| **Single-purpose roles** | Each role configures exactly one component. Reject creeping scope. |
| **Opt-in third-party** | Roles managing an external repo must default to disabled and leave the system clean if disabled. |
| **Optional dependencies** | `podman_disabled \| default(false)` or similar cross-role flags must use default defensively. |
| **Cross-role variable use** | When referencing another role's variable (e.g. `users_list`), always guard with `if VAR is defined else []` if the role must work standalone. |
| **Fact namespace** | All fact access must use `ansible_facts.fact_name`, never bare variable injection. |
| **Cross-distro gaps** | Roles must handle both `RedHat` and `Debian` `os_family` for different packages and system paths. |
| **Container environments** | Any role managing systemd units or networking must guard against `virtualization_type == 'container'` if expected to work in containers (dependencies of `baselinux`). |
| **argument_specs.yml** | All defaults variables in all roles require a precise argument_specs entry. |

## Variable naming

| Pattern | Meaning |
|---|---|
| `{role}_disabled: false` | Primary on/off switch for `general` roles; triggers uninstall or noop when `true`. |
| `{role}_enabled: false` | Opt-in on/off switch for `thirdparty` roles; triggers uninstall when `true`. |
| `{role}_{feature}_enabled` | Feature flag, typically derived from `not {role}_disabled`. |
| `{role}_{thing}_list` | List form of a nested dict variable, produced via `\| nested_dict_to_list('key_attr')`. |
| `{role}_{thing}` (dict) | Legacy, inventory-facing dict-of-dicts; tasks iterate the `_list` form. |
| `{role}_{thing}_pt_{part}` | Component included in `{role}_{thing}` to make partial overrides easy (e.g. `workstation`). |
| `{role}_{thing}_default` | Default value of `{role}_{thing}`; allows merging defaults in the inventory (e.g. `gnome`). |
| `{role}_packages` | List of cross-distro packages; flatten with set_fact in the role. |

## Role anatomy

```
roles/{name}/
  defaults/main.yml       # User-overridable variables (lowest precedence)
  vars/main.yml           # Internal computed variables (not user-facing)
  tasks/main.yml          # Entry point: block with {role} tag, include_tasks orchestration, role completed assert
  tasks/update.yml        # Optional update entrypoint for the oszi.general.update playbook
  tasks/{install,uninstall,config,deploy}.yml
  handlers/main.yml
  meta/main.yml           # Galaxy metadata + role dependencies
  meta/argument_specs.yml # Full documentation for every defaults variable (required)
  templates/              # absolute dest path as relative, .j2, e.g. templates/etc/app/app.conf.j2
  files/                  # absolute dest path as relative, e.g. files/etc/app/app.conf
```

## Privilege-aware paths (rootful vs rootless)

**Pre-condition:** `rootless`-tagged roles only.
Root-only roles assert root and use system paths unconditionally.

All paths must resolve correctly for both root and non-root:

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
package: "{{ (ansible_facts.os_family == 'RedHat') | ternary('toolbox', 'podman-toolbox') }}"

# Platform-specific package lists - set_fact with flatten before use
python_packages:
  - "{{ ['python3-devel', 'gcc'] if ansible_facts.os_family == 'RedHat' else [] }}"
  - "{{ ['python3-dev', 'build-essential'] if ansible_facts.os_family == 'Debian' else [] }}"
```

## Task structure pattern (tasks/main.yml)

Every `tasks/main.yml` follows a fixed structure: one top-level block tagged with the role name,
`include_tasks` orchestration inside, inter-role fact exports with `tags: [always]` (runs regardless
of `--tags` filtering), and a no-op role completed assert at the end.

Common alternative entrypoints are `tasks/update.yml` or `tasks/{role}.yml`. Alternative entrypoints
must be documented in `argument_specs.yml` (use yaml anchors for options).

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

`vars/main.yml` is evaluated at **role load time**, before any loop runs. Using a meaningful name
directly as `loop_var` when that name is already defined in `vars/main.yml` triggers an Ansible
warning; leaving it undefined at load time causes argument_specs validation to fail.
Solution - two-name convention:

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
  role_item_path: "{{ [base_path, role_item.name] | path_join }}"
```

## Galaxy tag rules (enforced by tests)

1. The collection name must be a tag: `general`, `thirdparty`, `environments`, `utils`
2. A mutually exclusive environment tag: `baselinux`, `containers`, `thirdparty`, `toolbox`, `workstation`
3. Rootless XOR root assertion: Roles must either add the `rootless` tag, or assert root privileges.

Accepted dependencies to assert root privileges:
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
