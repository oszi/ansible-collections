# Requires ./activate

VERBOSE    ?=
CHECK      ?=
CONNECTION ?=
LIMIT      ?=
TAGS       ?=
SKIP_TAGS  ?=

ANSIBLE_PLAYBOOK := . ./activate && ansible-playbook
ANSIBLE_ARGS = $(if $(VERBOSE), -vvv,)$(if $(CHECK), --check --diff,)$(if $(CONNECTION), --connection "$(CONNECTION)",)$(if $(LIMIT), --limit "$(LIMIT)",)$(if $(TAGS), --tags "$(TAGS)",)$(if $(SKIP_TAGS), --skip-tags "$(SKIP_TAGS)",)

localhost: LIMIT := $(shell hostname -f)
localhost: CONNECTION := local
localhost: workstation

baselinux containerhost toolbox workstation rootless: %: oszi.environments.%

update: %: oszi.general.%

debug versions: %: oszi.utils.%

playbooks/% oszi.environments.% oszi.general.% oszi.thirdparty.% oszi.utils.%: activate ansible.cfg FORCE
	$(ANSIBLE_PLAYBOOK) $(ANSIBLE_ARGS) $@

activate ansible.cfg:
	@test -f $@ || (echo "./$@ not found! Copy examples/$@"; exit 127)

.PHONY: FORCE
