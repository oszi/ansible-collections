SHELL := /bin/bash

all: localhost
localhost: export ANSIBLE_BECOME_ASK_PASS := True

include ../_scripts/_scripts.mk
include ../_scripts/_ansible.mk
