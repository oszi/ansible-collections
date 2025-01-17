# shellcheck shell=sh disable=SC1090 # non-constant source
# ansible managed skel

# See also /etc/{zsh/,}zprofile from the distribution.

# zshenv is always sourced first (unmanaged)
# zprofile is sourced for login shells (this file)
# zshrc is sourced for interactive shells
# zlogin again for login shells (unmanaged)
# zlogout finally at exit (unmanaged)

if [ -f ~/.profile ]; then
    . ~/.profile
fi
