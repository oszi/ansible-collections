# shellcheck shell=bash disable=SC2296 # zsh is unsupported
# shellcheck disable=SC2016,SC2034 # single quotes, variable appears unused

[ "$TERM" != "dumb" ] || return

autoload -Uz +X compinit && compinit

setopt COMPLETE_IN_WORD

_complete_reply() {
    if [[ "$_complete_last_try" != "${HISTNO}${BUFFER}${CURSOR}" ]]; then
        _complete_last_try="${HISTNO}${BUFFER}${CURSOR}"
        reply=(_complete _match _prefix _files)
    else
        reply=(_oldlist _complete _correct _approximate _files)
    fi
}

zstyle -e ':completion:*' completer _complete_reply
zstyle ':completion:*' verbose yes

zstyle ':completion:*:correct:*' insert-unambiguous true
zstyle ':completion:*:correct:*' original true

zstyle ':completion:*:approximate:*' max-errors 'reply=($((($#PREFIX+$#SUFFIX)/3)) numeric)'

zstyle ':completion:*:*:kill:*' command 'ps -u $UID -o pid=,tty=,cmd='
zstyle ':completion:*:*:kill:*' menu yes select

zstyle ':completion:*:default' list-colors "${(s.:.)LS_COLORS}"
