COLLECTIONS ?= $(shell test -d collections && echo collections || echo ..)
SCRIPTS     ?= $(shell test -d _scripts && echo _scripts || echo $(COLLECTIONS)/_scripts)
VENV        ?= $(COLLECTIONS)/venv

VENV_ACTIVATE := test -d $(VENV) && . $(VENV)/bin/activate \
	&& echo "INFO: venv activated." >&2 \
	|| echo "INFO: venv not activated. Using existing paths." >&2

all: FORCE

ifneq ($(filter $(VENV),venv ./venv),$(VENV))
.PHONY: venv
venv: $(VENV)
endif

$(VENV): $(COLLECTIONS)/requirements.txt $(COLLECTIONS)/requirements.yml
	python3 -m venv $(VENV) && . $(VENV)/bin/activate \
	&& pip install -r $(COLLECTIONS)/requirements.txt \
	&& ansible-galaxy collection install -r $(COLLECTIONS)/requirements.yml \
	&& touch $(VENV)

ifneq ($(filter $(COLLECTIONS),. ..),$(COLLECTIONS))
update-collections: FORCE
	$(MAKE) -C $(COLLECTIONS) reset
	VERSION=$$(git -C $(COLLECTIONS) describe --tags --exact-match 2>/dev/null \
		|| git -C $(COLLECTIONS) rev-parse --short HEAD) \
	&& git commit -S -n -m "Update ansible-collections [$${VERSION}]" $(COLLECTIONS) \
	&& git push --follow-tags
endif

tests: FORCE
	@$(VENV_ACTIVATE) && $(SCRIPTS)/run-tests.sh

reset: FORCE
	$(SCRIPTS)/git-reset.sh

clean: FORCE
	$(SCRIPTS)/git-reset.sh --force

.PHONY: FORCE
