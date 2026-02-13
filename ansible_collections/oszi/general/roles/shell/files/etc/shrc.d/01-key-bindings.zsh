# shellcheck shell=bash disable=SC2190,SC2296 # zsh is unsupported
# shellcheck disable=SC1091 # not following input sources

[ "$TERM" != "dumb" ] || return

if [ -f /usr/share/fzf/shell/key-bindings.zsh ]; then
    . /usr/share/fzf/shell/key-bindings.zsh
elif [ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]; then
    . /usr/share/doc/fzf/examples/key-bindings.zsh
fi

# Comprehensive space-separated key sequences covering various terminals and modes:
# * CSI sequences (^[[...): xterm, gnome-terminal, most modern terminals
# * SS3 sequences (^[O...): application mode
# * Tilde sequences: rxvt, linux console, PuTTY variants
typeset -g -A key2seq
key2seq=(
    # Backspace and Control+Backspace, sometimes indistinguishable.
    Backspace        '^? ^H'
    AltBackspace     '^[^? ^[^H'
    Insert           '^[[2~'
    Delete           '^[[3~'
    ControlDelete    '^[[3;5~'
    Home             '^[[H ^[OH ^[[1~ ^[[7~'
    End              '^[[F ^[OF ^[[4~ ^[[8~'
    PageUp           '^[[5~'
    PageDown         '^[[6~'
    Tab              '^I'
    ShiftTab         '^[[Z'
    Up               '^[[A ^[OA'
    Down             '^[[B ^[OB'
    Left             '^[[D ^[OD'
    Right            '^[[C ^[OC'
    ControlLeft      '^[[1;5D ^[[5D'
    ControlRight     '^[[1;5C ^[[5C'
    # Custom bindings
    EmacsWordStyle   '^[z'
    EmacsEditCmd     '^x^e'
    ViEditCmd        '^v'
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

    for seq in ${(s: :)sequences}; do
        for map in "${maps[@]}"; do
            bindkey -M "$map" "$seq" "$widget"
        done
    done
}

autoload -Uz edit-command-line
autoload -Uz up-line-or-beginning-search
autoload -Uz down-line-or-beginning-search
autoload -Uz select-word-style

zle -N edit-command-line
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
zle -N select-word-style

bind2maps emacs             -- Backspace        backward-delete-char
bind2maps       viins       -- Backspace        vi-backward-delete-char
bind2maps             vicmd -- Backspace        vi-backward-char
bind2maps emacs             -- AltBackspace     backward-kill-word
bind2maps       viins vicmd -- AltBackspace     vi-backward-kill-word
bind2maps emacs viins       -- Insert           overwrite-mode
bind2maps             vicmd -- Insert           vi-insert
bind2maps emacs             -- Delete           delete-char
bind2maps       viins vicmd -- Delete           vi-delete-char
bind2maps emacs viins vicmd -- ControlDelete    kill-word
bind2maps emacs             -- Home             beginning-of-line
bind2maps       viins vicmd -- Home             vi-beginning-of-line
bind2maps emacs             -- End              end-of-line
bind2maps       viins vicmd -- End              vi-end-of-line
bind2maps emacs viins vicmd -- PageUp           up-line-or-history
bind2maps emacs viins vicmd -- PageDown         down-line-or-history
bind2maps emacs viins vicmd -- Tab              expand-or-complete
bind2maps emacs viins vicmd -- ShiftTab         reverse-menu-complete
bind2maps emacs viins vicmd -- Up               up-line-or-beginning-search
bind2maps emacs viins vicmd -- Down             down-line-or-beginning-search
bind2maps emacs             -- Left             backward-char
bind2maps       viins vicmd -- Left             vi-backward-char
bind2maps emacs             -- Right            forward-char
bind2maps       viins vicmd -- Right            vi-forward-char
bind2maps emacs             -- ControlLeft      backward-word
bind2maps       viins vicmd -- ControlLeft      vi-backward-word
bind2maps emacs             -- ControlRight     forward-word
bind2maps       viins vicmd -- ControlRight     vi-forward-word

bind2maps emacs             -- EmacsWordStyle   select-word-style
bind2maps emacs             -- EmacsEditCmd     edit-command-line
bind2maps             vicmd -- ViEditCmd        edit-command-line

# history expansion on space (!N)
bindkey ' ' magic-space

unset -f bind2maps
unset key2seq
