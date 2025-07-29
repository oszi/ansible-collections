# Ansible managed skel
# shellcheck shell=sh disable=SC1090 # non-constant source

# See also /etc/{zsh/,}zprofile from the distribution.
# Sequence: zshenv > zprofile* > zshrc* > zlogin > zlogout

if [ -f ~/.profile ]; then
    . ~/.profile
fi
