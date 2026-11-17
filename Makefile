SHELL := /bin/bash
COLLECTIONS := .

include _scripts/_scripts.mk

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
