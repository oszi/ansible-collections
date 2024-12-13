# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source

if [ -f /etc/bashrc ]; then
    . /etc/bashrc
fi

case $- in
    *i*) ;;
      *) return ;;
esac

_source_glob() {
    for rc in "$@"; do
        if [ -r "$rc" ]; then
            . "$rc"
        fi
    done
    unset rc
}

if [ -n "${POSIXLY_CORRECT-}" ]; then
    _source_glob /etc/bashrc.d/x-*.sh
    _source_glob ~/.bashrc.d/x-*.sh
    return
fi

_source_glob /etc/bashrc.d/*
_source_glob ~/.bashrc.d/*
_source_glob ~/.bash_aliases

if [ -z "${BASH_COMPLETION_VERSINFO-}" ]; then
    _source_glob /usr/share/bash-completion/bash_completion
fi
