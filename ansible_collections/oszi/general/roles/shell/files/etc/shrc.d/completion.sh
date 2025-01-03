# shellcheck shell=sh disable=SC1091 # not following input sources

# .sh files are sourced before .bash and .zsh thus completion is guaranteed to
# be ready by when .bash and .zsh completion files (installed by other roles)
# are sourced. However, /etc/shrc.d is not the place for most completion files.

# Bash: /etc/bash_completion.d
# ZSH: /usr/{local/,}share/zsh/{site-functions,vendor-completions}

# Any exceptional, cross-compatible .sh completion file must be alphabetically
# ordered after this file.

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
