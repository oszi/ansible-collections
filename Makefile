SHELL := /bin/bash

VENV_ACTIVATE := test -d venv && . venv/bin/activate \
	&& echo "INFO: venv activated." >&2 \
	|| echo "INFO: venv not activated. Using existing paths." >&2

all: init tests

tests: FORCE
	@$(VENV_ACTIVATE) && _scripts/run-tests.sh

# galaxy-release.sh includes run-tests.sh
major minor patch: FORCE
	@$(VENV_ACTIVATE) && _scripts/galaxy-release.sh $@
	git push --follow-tags

venv: requirements.txt requirements.yml
	python3 -m venv venv && . venv/bin/activate \
	&& pip install -r requirements.txt \
	&& ansible-galaxy collection install -r requirements.yml \
	&& touch venv

init: FORCE
	_scripts/git-init.sh

reset: FORCE
	_scripts/git-reset.sh

clean: FORCE
	_scripts/git-reset.sh --force

.PHONY: FORCE
