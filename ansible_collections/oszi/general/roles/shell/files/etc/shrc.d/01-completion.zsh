# shellcheck shell=sh disable=SC2016 # single quotes

autoload -Uz +X compinit && compinit
autoload -Uz +X bashcompinit && bashcompinit

setopt COMPLETE_IN_WORD
setopt ALWAYS_TO_END

zstyle ':completion:*' completer _complete _ignored _files
zstyle ':completion:*' verbose yes

zstyle ':completion:*:kill:*' command 'ps -u $UID -o pid=,tty=,cmd='
zstyle ':completion:*:kill:*' menu yes select

zstyle ':completion:*:killall:*' command 'ps -u $UID -o comm='
zstyle ':completion:*:killall:*' menu yes select
