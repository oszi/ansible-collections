# \_scripts/tests

A collection of scripts for automated tests such as source code linting.

Stable interface to run tests:
```bash
_scripts/run-tests.sh # [--all|ansible-lint|ansible-test|ansible-vault|galaxy-tags|molecule|python|shellcheck] ...
```
`--all` runs every test, including opt-in tests, and passes `--all` to `ansible-lint`, `ansible-test`, `molecule`.

Arguments between `[` and `]` after a test name are passed to that test verbatim, including `--`.  
A literal `]` cannot be passed this way; run the test script directly instead.
```bash
_scripts/run-tests.sh ansible-lint [ --all ] molecule [ oszi.utils -- test --destroy never ]
```

Molecule tests are opt-in and run only when requested; see [MOLECULE.md](MOLECULE.md).  
Without arguments, only the roles affected since the previous release are tested:
```bash
_scripts/run-tests.sh molecule # '[' [--all] [--ignore-framework] [--list] [--workers N] \
  # [oszi.general.shell|oszi.utils ...] [-- MOLECULE_ARGS ...] ']'
```

Reformat python with black - check-only by default:
```bash
_scripts/run-tests.sh python [ --black ]
```

Without arguments, only the paths changed since the previous release are linted; whole roles if touched.  
Automatic selection respects ansible-lint's configured exclusions and discovery rules.  
Arguments after `--` are passed to ansible-lint verbatim:
```bash
_scripts/run-tests.sh ansible-lint # '[' [--all] [ansible_collections/... ...] [-- ANSIBLE_LINT_ARGS ...] ']'
```

The ansible-test test runs `ansible-test sanity` and `units` tests of the collections with docker/podman.  
Without arguments, any change since the previous release selects all sanity tests in its collection.  
Plugin/module source changes and `tests/unit` also select the full unit test suite in their collection.  
Explicit paths use the same rules; collection or unit-test parent directories, or `--all` select both suites.
```bash
_scripts/run-tests.sh ansible-test # '[' [--all] [--sanity] [--units] [ansible_collections/... ...] ']'
```

Under rootless podman, ansible-test uses the `podman` network to isolate tests from the network.  
If stopping containers fails with `rootless netns: kill network process: permission denied`,  
the Debian/Ubuntu AppArmor profile for `pasta` lacks a signal rule:
```bash
pasta_path=/etc/apparmor.d/usr.bin.pasta pasta_signal='signal (receive) peer={podman,unconfined},'
grep -qF "$pasta_signal" "$pasta_path" || sudo sed -z -i "s|}\n*\$|\n  ${pasta_signal}\n}\n|" "$pasta_path" \
&& sudo apparmor_parser -r "$pasta_path"
```
Avoid `--docker-network=bridge` as a workaround; tests are then not isolated from the network.

Tests are written in python, using a common library: [testlib](testlib)
