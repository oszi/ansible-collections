SHELL := /bin/bash

CHECK     ?=
LIMIT     ?=
TAGS      ?=
SKIP_TAGS ?=

ANSIBLE_PLAYBOOK ?= . ./activate && ansible-playbook
ANSIBLE_ARGS = $(if $(CHECK), --check --diff,)$(if $(LIMIT), --limit "$(LIMIT)",)$(if $(TAGS), --tags "$(TAGS)",)$(if $(SKIP_TAGS), --skip-tags "$(SKIP_TAGS)",)

localhost: export ANSIBLE_BECOME_ASK_PASS := True
localhost: ANSIBLE_PLAYBOOK := $(ANSIBLE_PLAYBOOK) --connection local --limit "$$(hostname -f)"
localhost: workstation

baselinux containerhost toolbox workstation: FORCE
	$(ANSIBLE_PLAYBOOK) $(ANSIBLE_ARGS) oszi.environments.$@

update versions: FORCE
	$(ANSIBLE_PLAYBOOK) $(ANSIBLE_ARGS) oszi.general.$@

oszi.% playbooks/%: FORCE
	$(ANSIBLE_PLAYBOOK) $(ANSIBLE_ARGS) $@

venv: collections/.git collections/requirements.txt collections/requirements.yml
	python3 -m venv venv && . venv/bin/activate \
	&& pip install -r collections/requirements.txt \
	&& ansible-galaxy collection install -r collections/requirements.yml \
	&& touch venv

FORCE: collections/.git
collections/.git:
	../_scripts/git-init.sh

reset: FORCE
	../_scripts/git-reset.sh

clean: FORCE
	../_scripts/git-reset.sh --force

.PHONY: FORCE
