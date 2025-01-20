# shellcheck shell=bash disable=SC2190 # zsh is unsupported
# shellcheck disable=SC1091,SC2154 # not following input sources, terminfo not assigned

[ "$TERM" != "dumb" ] || return

zmodload zsh/terminfo

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

if [ -f /usr/share/fzf/shell/key-bindings.zsh ]; then
    . /usr/share/fzf/shell/key-bindings.zsh
elif [ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]; then
    . /usr/share/doc/fzf/examples/key-bindings.zsh
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
    Tab              '^I'
    ShiftTab         "${terminfo[kcbt]}"  # ^[[Z
    Up               "${terminfo[kcuu1]}" # ^[[A
    Down             "${terminfo[kcud1]}" # ^[[B
    Left             "${terminfo[kcub1]}" # ^[[D
    Right            "${terminfo[kcuf1]}" # ^[[C
    # [Non-standard ncurses extensions]
    ControlLeft      "${terminfo[kLFT5]:-^[[1;5D}"
    ControlRight     "${terminfo[kRIT5]:-^[[1;5C}"
    # [Not found in terminfo]
    ControlBackspace '^H'
    ControlDelete    '^[[3;5~'
    AltBackslash     $'^[\\'
    EmacsEditor      '^x^e'
    ViEditor         '^v'
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

    [[ -n "$sequence" ]] || return 1
    [[ -n "$widget"   ]] || return 1

    for i in "${maps[@]}"; do
        bindkey -M "$i" "$sequence" "$widget"
    done
}

typeset -g WORDCHARS_ORIG
typeset -g WORDCHARS_PATH_MODE=',.-_+~!$%*()[]{}'  # excluding /\|@#?&;:=<>'"

function wordchars-mode-switch() {  # vi wordchars are different!
    if [[ "$WORDCHARS" != "$WORDCHARS_PATH_MODE" ]]; then
        WORDCHARS_ORIG="$WORDCHARS"
        WORDCHARS="$WORDCHARS_PATH_MODE"
    elif [[ -n "$WORDCHARS_ORIG" ]]; then
        WORDCHARS="$WORDCHARS_ORIG"
    fi
}

function edit-command-line-fixed() {
    zle zle-line-finish
    edit-command-line
    zle zle-line-init
    zle reset-prompt
}

autoload -Uz edit-command-line
autoload -Uz up-line-or-beginning-search
autoload -Uz down-line-or-beginning-search

zle -N wordchars-mode-switch
zle -N edit-command-line edit-command-line-fixed
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
bind2maps emacs             -- ControlBackspace backward-kill-word
bind2maps       viins vicmd -- ControlBackspace vi-backward-kill-word
bind2maps emacs viins vicmd -- ControlDelete    kill-word
bind2maps emacs             -- AltBackslash     wordchars-mode-switch
bind2maps emacs             -- EmacsEditor      edit-command-line
bind2maps             vicmd -- ViEditor         edit-command-line

# history expansion on space (!N)
bindkey ' ' magic-space

unset -f bind2maps
unset key
