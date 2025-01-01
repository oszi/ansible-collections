# shellcheck shell=sh disable=SC1091 # not following input sources

# *.sh files are sourced earlier than *.bash and *.zsh so completion is
# guaranteed to be ready by when external completion files are sourced
# but exceptional *.sh completion files must be ordered after this file.

# Prefer /etc/bash_completion.d/ and /usr/local/share/zsh/site-functions/
# for third-party software instead of /etc/shrc.d/ ...

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
