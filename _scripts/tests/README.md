# \_scripts/tests

A collection of scripts for automated tests such as source code linting.

Stable interface to run tests:
```bash
_scripts/run-tests.sh  # [ansible-lint|ansible-vault|galaxy-tags|molecule|python|shellcheck] ...
```

Arguments between `[` and `]` after a test name are passed to that test verbatim, including `--`.  
A literal `]` cannot be passed this way; run the test script directly instead.
```bash
_scripts/run-tests.sh python [ --black ] molecule [ oszi.general.shell -- test --destroy never ]
```

Molecule tests are opt-in (`# run-tests: opt-in`) and run only when requested; see [MOLECULE.md](MOLECULE.md).  
Without arguments, only the roles affected since the previous release are tested:
```bash
_scripts/tests/molecule.py  # [--all] [--ignore-framework] [--list] [oszi.general.shell|oszi.utils ...] [-- MOLECULE_ARGS ...]
```

Reformat python with black (check-only by default):
```bash
_scripts/tests/python.py --black
```

Tests are written in python, using a common library: [testlib.py](testlib.py)
