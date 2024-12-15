# shellcheck shell=sh disable=SC1091 # not following input sources

case $- in
    *i*) ;;
      *) return ;;
esac

if [ -f /usr/share/fzf/shell/key-bindings.bash ]; then
    . /usr/share/fzf/shell/key-bindings.bash
elif [ -f /usr/share/doc/fzf/examples/key-bindings.bash ]; then
    . /usr/share/doc/fzf/examples/key-bindings.bash
fi
