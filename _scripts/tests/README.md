# _scripts/tests

_scripts/tests is a collection of scripts for automated tests such as source code linting.

Stable interface to run tests:
```bash
_scripts/run-tests.sh  # [ansible-lint|ansible-vault|galaxy-tags|python|shellcheck]
```

Reformat python with black (check-only by default):
```bash
_scripts/tests/python.py --black
```

Tests are written in python, using a common library: [testlib.py](testlib.py)
