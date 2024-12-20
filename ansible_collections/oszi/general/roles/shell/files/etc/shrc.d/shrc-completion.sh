# shellcheck shell=sh disable=SC1091 # not following input sources
# shellcheck disable=SC3044 # in POSIX complete is undefined

# *.sh is sourced earlier than *.bash and *.zsh so completion is guaranteed
# to be ready by when external completion files are sourced.
if [ -n "${BASH_VERSION-}" ] && [ -z "${BASH_COMPLETION_VERSINFO-}" ]; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi

# Abort immediately if completion is not supported.
if ! type complete >/dev/null 2>&1; then
    return
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

# _completion_loader is undefined in ZSH but it supports aliases.
if ! type _completion_loader >/dev/null 2>&1; then
    return
fi

_completion_loader ssh
if type _ssh >/dev/null 2>&1; then
    complete -o nospace -F _ssh ssh-forget
    complete -o nospace -F _ssh ssh-proxied
fi

_completion_loader scp
if type _scp >/dev/null 2>&1; then
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
