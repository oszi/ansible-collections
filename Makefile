SHELL := /bin/bash
COLLECTIONS := .

include _scripts/_scripts.mk

venv: $(VENV)/.lock FORCE

# Prefer collections bundled in the ansible python package (no -U for galaxy install).
$(VENV)/.lock: requirements.txt requirements.yml
	python3 -m venv $(VENV) && . $(VENV)/bin/activate \
	&& pip install -U -r requirements.txt \
	&& ansible-galaxy collection install -r requirements.yml -p $(COLLECTIONS) \
	&& touch $(VENV)/.lock

# galaxy-release.sh includes run-tests.sh
major minor patch: FORCE
	@$(VENV_ACTIVATE) && $(SCRIPTS)/galaxy-release.sh $@
	git push --follow-tags

MOLECULE_ARGS ?= --ignore-framework
molecule: FORCE
	@$(VENV_ACTIVATE) && $(SCRIPTS)/run-tests.sh $@ [ $(MOLECULE_ARGS) ]

molecule-all: MOLECULE_ARGS := --all
molecule-all: molecule

molecule-list: MOLECULE_ARGS := --ignore-framework --list
molecule-list: molecule

molecule-reset: MOLECULE_ARGS := --all -- reset
molecule-reset: molecule
