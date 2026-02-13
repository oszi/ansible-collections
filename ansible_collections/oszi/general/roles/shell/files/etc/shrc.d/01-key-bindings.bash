# shellcheck shell=bash
# shellcheck disable=SC1091 # not following input sources

[ "$TERM" != "dumb" ] || return

if [ -f /usr/share/fzf/shell/key-bindings.bash ]; then
    . /usr/share/fzf/shell/key-bindings.bash
elif [ -f /usr/share/doc/fzf/examples/key-bindings.bash ]; then
    . /usr/share/doc/fzf/examples/key-bindings.bash
fi

((BASH_VERSINFO[0] >= 4)) || return

# Comprehensive space-separated key sequences covering various terminals and modes:
# * CSI sequences (\e[...): xterm, gnome-terminal, most modern terminals
# * SS3 sequences (\eO...): application mode
# * Tilde sequences: rxvt, linux console, PuTTY variants
declare -A key2seq=(
    # Backspace and Control+Backspace, sometimes indistinguishable.
    [Backspace]='\C-? \C-h'
    [AltBackspace]='\e\C-? \e\C-h'
    [Insert]='\e[2~'
    [Delete]='\e[3~'
    [ControlDelete]='\e[3;5~'
    [Home]='\e[H \eOH \e[1~ \e[7~'
    [End]='\e[F \eOF \e[4~ \e[8~'
    [PageUp]='\e[5~'
    [PageDown]='\e[6~'
    [Tab]='\C-i'
    [ShiftTab]='\e[Z'
    [Up]='\e[A \eOA'
    [Down]='\e[B \eOB'
    [Left]='\e[D \eOD'
    [Right]='\e[C \eOC'
    [ControlLeft]='\e[1;5D \e[5D'
    [ControlRight]='\e[1;5C \e[5C'
    # Custom bindings
    [EmacsEditCmd]='\C-x\C-e'
    [ViEditCmd]='\C-v'
)

function bind2maps() {
    local key sequences seq map widget
    local -a maps

    while [[ "$1" != "--" ]]; do
        maps+=("$1")
        shift
    done
    shift

    key="$1"
    sequences="${key2seq[$key]}"
    widget="$2"

    [[ -n "$sequences" ]] || return 1
    [[ -n "$widget"    ]] || return 1

    for seq in $sequences; do
        for map in "${maps[@]}"; do
            bind -m "$map" "\"${seq}\": ${widget}"
        done
    done
}

bind2maps emacs vi-insert            -- Backspace       backward-delete-char
bind2maps                 vi-command -- Backspace       backward-char
bind2maps emacs vi-insert vi-command -- AltBackspace    backward-kill-word
bind2maps emacs vi-insert            -- Insert          overwrite-mode
bind2maps                 vi-command -- Insert          vi-insertion-mode
bind2maps emacs vi-insert vi-command -- Delete          delete-char
bind2maps emacs vi-insert vi-command -- ControlDelete   kill-word
bind2maps emacs vi-insert vi-command -- Home            beginning-of-line
bind2maps emacs vi-insert vi-command -- End             end-of-line
bind2maps emacs vi-insert vi-command -- PageUp          previous-history
bind2maps emacs vi-insert vi-command -- PageDown        next-history
bind2maps emacs vi-insert vi-command -- Tab             complete
bind2maps emacs vi-insert vi-command -- ShiftTab        menu-complete
bind2maps emacs vi-insert vi-command -- Up              history-search-backward
bind2maps emacs vi-insert vi-command -- Down            history-search-forward
bind2maps emacs vi-insert vi-command -- Left            backward-char
bind2maps emacs vi-insert vi-command -- Right           forward-char
bind2maps emacs vi-insert vi-command -- ControlLeft     backward-word
bind2maps emacs vi-insert vi-command -- ControlRight    forward-word

bind2maps emacs                      -- EmacsEditCmd    edit-and-execute-command
bind2maps                 vi-command -- ViEditCmd       edit-and-execute-command

# history expansion on space (!N)
bind '" ": magic-space'

unset -f bind2maps
unset key2seq
