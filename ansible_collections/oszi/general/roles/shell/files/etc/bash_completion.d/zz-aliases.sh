# shellcheck shell=bash

_completion_loader ssh
if type -t _ssh >/dev/null 2>&1; then
    complete -o nospace -F _ssh ssh-forget
    complete -o nospace -F _ssh ssh-proxied
fi

_completion_loader scp
if type -t _scp >/dev/null 2>&1; then
    complete -o nospace -F _scp scp-forget
    complete -o nospace -F _scp scp-proxied
fi

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
