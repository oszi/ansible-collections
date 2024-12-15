# shellcheck shell=sh disable=SC1091 # not following input sources

case $- in
    *i*) ;;
      *) return ;;
esac

if [ -f /usr/share/fzf/shell/key-bindings.zsh ]; then
    . /usr/share/fzf/shell/key-bindings.zsh
elif [ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]; then
    . /usr/share/doc/fzf/examples/key-bindings.zsh
fi
