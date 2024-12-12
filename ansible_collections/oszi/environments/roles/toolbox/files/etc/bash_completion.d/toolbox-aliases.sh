# shellcheck shell=bash

if command -v git >/dev/null 2>&1; then
    _completion_loader git
    complete -o bashdefault -o default -o nospace -F __git_wrap__git_main g
fi

if command -v kubectl >/dev/null 2>&1; then
    _completion_loader kubectl
    complete -o default -F __start_kubectl k
fi

if command -v tofu >/dev/null 2>&1; then
    complete -C tofu tofu
fi

if command -v terraform >/dev/null 2>&1; then
    complete -C terraform terraform
    complete -C terraform tf
elif command -v tofu >/dev/null 2>&1; then
    complete -C tofu tf
fi
