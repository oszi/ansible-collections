# Ansible Collection - oszi.utils

Ansible collection for ansible plugins and utility roles.

* Includes [filter](plugins/filter) and [lookup](plugins/lookup) plugins required by the collections.
* Utility playbooks target **all** hosts or the ansible controller and do not alter hosts.
* Utility roles mainly target the ansible controller and do not alter hosts.
* For example, gather **facts** and **bootstrap** SSH connections.

## Filter examples

**Computed list pattern** - `_list` is derived in `defaults/main.yml`; inventory sets only the dict:
```yaml
podman_networks_list: "{{ podman_networks | oszi.utils.nested_dict_to_list('name') }}"
podman_networks: {}  # inventory sets this
```

**Inventory-side merge pattern** - `_list` is derived in the inventory to combine multiple dicts:
```yaml
users_list: "{{ inventory_users_all | combine(inventory_users_workstations, list_merge='append_rp',
  recursive=true) | oszi.utils.nested_dict_to_list('name') }}"
```

**Shell-escaped, home-dir relative path** - Convert an absolute path into `~/'path'`:

```yaml
shell_shrc_safe_path: "{{ shell_shrc_path | oszi.utils.to_quoted_tilde_path(ansible_facts.user_dir) }}"
```

## Lookup examples

**Escape paths in systemd template units**

```yaml
podman_kube_service: "{{ lookup('oszi.utils.systemd_escape', podman_kube_spec_path,
  template=podman_kube_template_service) }}"
```

## Utility role examples

Use **facts** and **assert** as dependencies in `meta/main.yml`:

```yaml
dependencies:
  - role: oszi.utils.facts  # default facts, deduplicated
  - role: oszi.utils.facts
    vars:
      facts_subset: [hardware]
  - role: oszi.utils.facts
    vars:
      facts_subset: [network]
  - role: oszi.utils.assert  # if not tagged as rootless
    vars:
      assert_task_msg: "Assert root privileges"
      assert_that:
        - "ansible_facts.user_uid | int == 0"
```
