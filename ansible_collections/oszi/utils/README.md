# Ansible Collection - oszi.utils

Ansible collection for ansible plugins and utility roles.

## Collection Rules

* All custom [filter](plugins/filter) and [lookup](plugins/lookup) plugins are in the utils collection.
* Utility playbooks target **all** hosts or the ansible controller and do not alter hosts.
* Utility roles mainly target the ansible controller and do not alter hosts.

## Filter examples

**Nested dict to list pattern** - Combine multiple dicts into a nested dict before making a list:
```yaml
podman_quadlets_list: "{{ {} | oszi.utils.update_nested_dict(podman_quadlets, 'quadlet')
  | oszi.utils.update_nested_dict(podman_quadlets_copy_files, 'files')
  | oszi.utils.nested_dict_to_list('name') }}"  # key_attribute:name = dict key
```

**Shell-escaped, home-dir relative path** - Transform an absolute path into `~/'path'`:

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
      facts_subset: [network]
  - role: oszi.utils.assert  # if not tagged as rootless
    vars:
      assert_task_msg: "Assert root privileges"
      assert_that:
        - "ansible_facts.user_uid | int == 0"
```
