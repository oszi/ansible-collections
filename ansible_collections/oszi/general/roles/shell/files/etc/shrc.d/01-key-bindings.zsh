# shellcheck shell=bash disable=SC2190 # zsh is unsupported
# shellcheck disable=SC1091,SC2154 # not following input sources, terminfo not assigned

# Make sure that the terminal is in application mode when zle is active,
# since only then values from $terminfo are valid.
if (( ${+terminfo[smkx]} )) && (( ${+terminfo[rmkx]} )); then
    function zle-line-init() {
        printf '%s' "${terminfo[smkx]}"
    }

    function zle-line-finish() {
        printf '%s' "${terminfo[rmkx]}"
    }

    zle -N zle-line-init
    zle -N zle-line-finish
fi

typeset -g -A key
key=(
    Backspace        "${terminfo[kbs]}"   # ^?
    Insert           "${terminfo[kich1]}" # ^[[2~
    Delete           "${terminfo[kdch1]}" # ^[[3~
    Home             "${terminfo[khome]}" # ^[[H
    End              "${terminfo[kend]}"  # ^[[F
    PageUp           "${terminfo[kpp]}"   # ^[[5~
    PageDown         "${terminfo[knp]}"   # ^[[6~
    ShiftTab         "${terminfo[kcbt]}"  # ^[[Z
    Up               "${terminfo[kcuu1]}" # ^[[A
    Down             "${terminfo[kcud1]}" # ^[[B
    Left             "${terminfo[kcub1]}" # ^[[D
    Right            "${terminfo[kcuf1]}" # ^[[C
    ControlLeft      "${terminfo[kLFT5]}" # ^[[1;5D
    ControlRight     "${terminfo[kRIT5]}" # ^[[1;5C
    ControlBackspace '^H'
    ControlDelete    '^[[3;5~'
)

function bind2maps() {
    local i sequence widget
    local -a maps

    while [[ "$1" != "--" ]]; do
        maps+=("$1")
        shift
    done
    shift

    sequence="${key[$1]}"
    widget="$2"

    [[ -z "$sequence" ]] && return 1

    for i in "${maps[@]}"; do
        bindkey -M "$i" "$sequence" "$widget"
    done
}

if [ -f /usr/share/fzf/shell/key-bindings.zsh ]; then
    . /usr/share/fzf/shell/key-bindings.zsh
elif [ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]; then
    . /usr/share/doc/fzf/examples/key-bindings.zsh
fi

autoload -Uz up-line-or-beginning-search
autoload -Uz down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search

bind2maps emacs             -- Backspace        backward-delete-char
bind2maps       viins       -- Backspace        vi-backward-delete-char
bind2maps             vicmd -- Backspace        vi-backward-char
bind2maps emacs viins       -- Insert           overwrite-mode
bind2maps             vicmd -- Insert           vi-insert
bind2maps emacs             -- Delete           delete-char
bind2maps       viins vicmd -- Delete           vi-delete-char
bind2maps emacs             -- Home             beginning-of-line
bind2maps       viins vicmd -- Home             vi-beginning-of-line
bind2maps emacs             -- End              end-of-line
bind2maps       viins vicmd -- End              vi-end-of-line
bind2maps emacs viins vicmd -- PageUp           up-line-or-history
bind2maps emacs viins vicmd -- PageDown         down-line-or-history
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
bind2maps emacs             -- ControlBackspace backward-kill-word
bind2maps       viins vicmd -- ControlBackspace vi-backward-kill-word
bind2maps emacs viins vicmd -- ControlDelete    kill-word

bindkey '\ew' kill-region          # [Esc+w]
bindkey '\em' copy-prev-shell-word # [Esc+m]

unset -f bind2maps
unset key
