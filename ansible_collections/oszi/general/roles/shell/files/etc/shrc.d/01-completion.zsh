# shellcheck shell=bash disable=SC2296,SC2298 # zsh is unsupported
# shellcheck disable=SC2016,SC2034 # single quotes, variable appears unused
# shellcheck disable=SC1090 # non-constant source

autoload -Uz +X compinit && compinit
autoload -Uz +X bashcompinit && bashcompinit

setopt COMPLETE_IN_WORD

zstyle ':completion:*' completer _complete _match _prefix _approximate _files
zstyle ':completion:*' verbose yes

zstyle ':completion:*:approximate:*' max-errors 'reply=($((($#PREFIX+$#SUFFIX)/3)) numeric)'

zstyle ':completion:*:*:kill:*' command 'ps -u $UID -o pid=,tty=,cmd='
zstyle ':completion:*:*:kill:*' menu yes select

zstyle ':completion:*:default' list-colors "${(s.:.)LS_COLORS}"

# Try loading bash completions for commands that have no native completion.
# See the key-binding below. Your mileage may vary.

typeset -g -r -a _BASH_COMPLETIONS_PATH=(/etc/bash_completion.d /usr/share/bash-completion/completions)
typeset -g -A _bash_completions_tried

function _bash_complete_fallback() {
    local BASH_SOURCE
    local _cmd=${${(zA)BUFFER}[1]:t}

    if [[ $_cmd && ! ${_bash_completions_tried[$_cmd]} ]]; then
        rehash
        if ! whence "_${_cmd}" >/dev/null 2>&1; then
            for BASH_SOURCE in ${^_BASH_COMPLETIONS_PATH}/${_cmd}; do
                if [[ -r "$BASH_SOURCE" ]]; then
                    emulate ksh -c '. "$BASH_SOURCE"'
                    zle reset-prompt
                    break
                fi
            done
        fi
        _bash_completions_tried[$_cmd]=1
    fi

    zle complete-word
}

zle -N bash-complete-fallback _bash_complete_fallback
bindkey '\e\t' bash-complete-fallback # [Esc+Tab]
