# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed skel

case $- in
    *i*) ;;
      *) return ;;
esac

if [ -f /etc/bashrc ]; then
    . /etc/bashrc
elif [ -f /etc/bash.bashrc ]; then
    . /etc/bash.bashrc
fi

. /etc/shrc

if [ -z "${POSIXLY_CORRECT-}" ]; then
    source_glob ~/.bashrc.d/* ~/.bash_aliases
fi
