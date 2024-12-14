# shellcheck shell=sh disable=SC1090 # non-constant source
# ansible managed skel

case $- in
    *i*)
        # .zshrc is sourced in interactive mode
        ;;
    *)
        if [ -f ~/.profile ]; then
            . ~/.profile
        fi
        ;;
esac
