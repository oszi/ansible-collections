# Requires _scripts/_scripts.mk

CHECK     ?=
LIMIT     ?=
TAGS      ?=
SKIP_TAGS ?=

ANSIBLE_PLAYBOOK ?= . ./activate && ansible-playbook
ANSIBLE_ARGS = $(if $(CHECK), --check --diff,)$(if $(LIMIT), --limit "$(LIMIT)",)$(if $(TAGS), --tags "$(TAGS)",)$(if $(SKIP_TAGS), --skip-tags "$(SKIP_TAGS)",)

localhost: ANSIBLE_PLAYBOOK := $(ANSIBLE_PLAYBOOK) --connection local --limit "$$(hostname -f)"
localhost: workstation

baselinux containerhost toolbox workstation rootless: FORCE
	$(ANSIBLE_PLAYBOOK) $(ANSIBLE_ARGS) oszi.environments.$@

update versions: FORCE
	$(ANSIBLE_PLAYBOOK) $(ANSIBLE_ARGS) oszi.general.$@

oszi.% playbooks/%: FORCE
	$(ANSIBLE_PLAYBOOK) $(ANSIBLE_ARGS) $@

.PHONY: FORCE
