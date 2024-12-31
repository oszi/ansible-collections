# shellcheck shell=sh disable=SC1091 # not following input sources

# *.sh is sourced earlier than *.bash and *.zsh so completion is guaranteed
# to be ready by when external completion files are sourced.

# *.sh completion files must be ordered after this file.

if [ -n "${BASH_VERSION-}" ] && [ -z "${BASH_COMPLETION_VERSINFO-}" ] \
        && [ -z "${POSIXLY_CORRECT-}" ]; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi

if [ -n "${ZSH_VERSION-}" ]; then
    autoload -Uz +X compinit && compinit
    autoload -Uz +X bashcompinit && bashcompinit
    zstyle ':completion:*' completer _complete _ignored _files
fi
