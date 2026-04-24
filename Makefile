SHELL := /bin/bash
COLLECTIONS := .

include _scripts/_scripts.mk

# galaxy-release.sh includes run-tests.sh
major minor patch: FORCE
	@$(VENV_ACTIVATE) && $(SCRIPTS)/galaxy-release.sh $@
	git push --follow-tags
