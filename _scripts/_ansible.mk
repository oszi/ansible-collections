# Requires ./activate and ./ansible.cfg
ANSIBLE_PLAYBOOK := . ./activate && ansible-playbook

ANSIBLE_VERBOSE    ?=
ANSIBLE_CHECK      ?=
ANSIBLE_CONNECTION ?=
ANSIBLE_LIMIT      ?=
ANSIBLE_TAGS       ?=
ANSIBLE_SKIP_TAGS  ?=

_CMD_FLAG = $(if $(filter 1 Y y Yes YES yes True TRUE true,$(value $(2))), $(1),)
_CMD_ARG  = $(if $(value $(2)), $(1) '$(subst ','\'',$(value $(2)))',)

ANSIBLE_ARGS += $\
	$(call _CMD_FLAG,-vvv,ANSIBLE_VERBOSE)$\
	$(call _CMD_FLAG,--check --diff,ANSIBLE_CHECK)$\
	$(call _CMD_ARG,--connection,ANSIBLE_CONNECTION)$\
	$(call _CMD_ARG,--limit,ANSIBLE_LIMIT)$\
	$(call _CMD_ARG,--tags,ANSIBLE_TAGS)$\
	$(call _CMD_ARG,--skip-tags,ANSIBLE_SKIP_TAGS)

localhost: ANSIBLE_LIMIT := $(shell hostname -f)
localhost: ANSIBLE_CONNECTION := local
localhost: workstation

baselinux containerhost toolbox workstation update: %: oszi.environments.%

debug versions: %: oszi.utils.%

playbooks/% oszi.environments.% oszi.general.% oszi.thirdparty.% oszi.utils.%: activate ansible.cfg FORCE
	$(ANSIBLE_PLAYBOOK) $(ANSIBLE_ARGS) $@; \
	rc=$$?; printf "\007"; exit $$rc;

activate ansible.cfg:
	@test -f $@ || (echo "./$@ not found! Copy examples/$@"; exit 127)

.PHONY: FORCE
