# shellcheck shell=bash disable=SC2296,SC2299 # zsh is unsupported
# shellcheck disable=SC2016,SC2034 # single quotes, variable appears unused
# shellcheck disable=SC2154 # functions and compdef not assigned

[ "$TERM" != "dumb" ] || return

if ! (( ${+functions[compdef]} )); then
    autoload -Uz compinit
    compinit
fi

setopt COMPLETE_IN_WORD

function _completer_reply() {
    if [[ "$_complete_last_try" != "${HISTNO}${BUFFER}${CURSOR}" ]]; then
        _complete_last_try="${HISTNO}${BUFFER}${CURSOR}"
        reply=(_complete _match _prefix _files)
    else
        reply=(_oldlist _complete _correct _approximate _files)
    fi
}

zstyle -e ':completion:*' completer _completer_reply
zstyle ':completion:*' verbose yes

zstyle ':completion:*:correct:*' insert-unambiguous true
zstyle ':completion:*:correct:*' original true

zstyle ':completion:*:approximate:*' max-errors 'reply=($((($#PREFIX+$#SUFFIX)/3)) numeric)'

zstyle ':completion:*:*:kill:*' command "ps ${${${UID#0}:+xo}:-axo} pid=,tty=,user=,cmd="
zstyle ':completion:*:*:kill:*' menu yes select search
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'

zstyle ':completion:*:default' list-colors "${(s.:.)LS_COLORS}"
