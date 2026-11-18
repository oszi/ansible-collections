COLLECTIONS ?= $(shell test -d collections && echo collections || echo ..)
SCRIPTS     ?= $(shell test -d _scripts && echo _scripts || echo $(COLLECTIONS)/_scripts)
VENV        ?= $(COLLECTIONS)/venv

VENV_ACTIVATE := test -d $(VENV) && . $(VENV)/bin/activate \
	&& printf "INFO: venv activated. \U0001F40D\n" >&2 \
	|| printf "INFO: venv not activated. Using existing python paths.\n" >&2

all: FORCE

ifneq ($(filter $(COLLECTIONS),. ..),$(COLLECTIONS))
update-collections: FORCE
	$(MAKE) -C $(COLLECTIONS) reset
	@VERSION=$$(git -C $(COLLECTIONS) describe --tags --exact-match --match='[0-9]*.[0-9]*.[0-9]*' 2>/dev/null \
		|| git -C $(COLLECTIONS) rev-parse --short HEAD) && set -x \
	&& git commit -S -n -m "Update ansible-collections [$${VERSION}]" $(COLLECTIONS) \
	&& git push --follow-tags
endif

TESTS_ARGS ?=
tests: FORCE
	@$(VENV_ACTIVATE) && $(SCRIPTS)/run-tests.sh $(TESTS_ARGS)

reset: FORCE
	$(SCRIPTS)/git-reset.sh --force

clean: FORCE
	git clean -xfd -e /$(notdir $(VENV))
	git submodule foreach --recursive git clean -xfd -e /$(notdir $(VENV))

verify: FORCE
	$(SCRIPTS)/git-verify.sh

.PHONY: FORCE
