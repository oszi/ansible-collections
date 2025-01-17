# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed skel

# See also /etc/{zsh/,}zshrc from the distribution.

# zshenv is always sourced first (unmanaged)
# zprofile is sourced for login shells
# zshrc is sourced for interactive shells (this file)
# zlogin again for login shells (unmanaged)
# zlogout finally at exit (unmanaged)

. /etc/shrc

if [ -d ~/.zshrc.d ]; then
    source_glob ~/.zshrc.d/*
fi
