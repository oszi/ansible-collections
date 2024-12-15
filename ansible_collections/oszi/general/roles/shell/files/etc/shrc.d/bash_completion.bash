# shellcheck shell=sh disable=SC1091 # not following input sources

case $- in
    *i*) ;;
      *) return ;;
esac

if [ -z "${POSIXLY_CORRECT-}" ] && [ -z "${BASH_COMPLETION_VERSINFO-}" ]; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi
