COLLECTIONS ?= $(shell test -d collections && echo collections || echo ..)
SCRIPTS     ?= $(shell test -d _scripts && echo _scripts || echo $(COLLECTIONS)/_scripts)
VENV        ?= $(COLLECTIONS)/venv

VENV_ACTIVATE := test -d $(VENV) && . $(VENV)/bin/activate \
	&& echo "INFO: venv activated." >&2 \
	|| echo "INFO: venv not activated. Using existing paths." >&2

GIT_HOOKS := $(shell git rev-parse --git-dir)/hooks

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

tests: FORCE
	@$(VENV_ACTIVATE) && $(SCRIPTS)/run-tests.sh

reset: FORCE
	$(SCRIPTS)/git-reset.sh

clean: FORCE
	$(SCRIPTS)/git-reset.sh --force

# Init collections submodule (and hooks) where .git is a file.
ifneq ($(filter $(COLLECTIONS),. ..),$(COLLECTIONS))
FORCE: $(GIT_HOOKS)/pre-commit $(COLLECTIONS)/.git
$(GIT_HOOKS)/pre-commit $(COLLECTIONS)/.git $(COLLECTIONS)/requirements.txt $(COLLECTIONS)/requirements.yml &:
	$(SCRIPTS)/git-init.sh
else
FORCE: $(GIT_HOOKS)/pre-commit
$(GIT_HOOKS)/pre-commit:
	$(SCRIPTS)/git-init.sh
endif

.PHONY: FORCE
