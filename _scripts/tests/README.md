# \_scripts/tests

A collection of scripts for automated tests such as source code linting.

Stable interface to run tests:
```bash
_scripts/run-tests.sh # [--all|ansible-lint|ansible-test|ansible-vault|galaxy-tags|molecule|python|shellcheck] ...
```

`--all` runs every test, including opt-in tests, and passes `--all` to `ansible-lint` and `molecule`.

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
_scripts/run-tests.sh ansible-lint # '[' [--all] [ansible_collections/oszi/utils ...] [-- ANSIBLE_LINT_ARGS ...] ']'
```

The ansible-test test runs `ansible-test sanity` and `units` tests of the collections with docker/podman.  
Paths select collections, files or directories; ansible-test needs a writable `/tmp` (e.g., agents).  
Plugin source paths select all unit tests; paths under `tests/unit` select specific tests.
```bash
_scripts/run-tests.sh ansible-test # '[' [--sanity] [--units] [ansible_collections/oszi/utils/plugins/ ...] ']'
```

Tests are written in python, using a common library: [testlib.py](testlib.py)
