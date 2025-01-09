# shellcheck shell=sh disable=SC1091 # not following input sources

if [ -f /usr/share/fzf/shell/key-bindings.zsh ]; then
    . /usr/share/fzf/shell/key-bindings.zsh
elif [ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]; then
    . /usr/share/doc/fzf/examples/key-bindings.zsh
fi

# If the terminal is in application mode (smkx), translate keys
# to make them appear the same as in raw mode (rmkx).
bindkey -s '^[OH' '^[[H'  # Home
bindkey -s '^[OF' '^[[F'  # End
bindkey -s '^[OA' '^[[A'  # Up
bindkey -s '^[OB' '^[[B'  # Down
bindkey -s '^[OD' '^[[D'  # Left
bindkey -s '^[OC' '^[[C'  # Right

# TTY sends different key codes, translate them to regular.
bindkey -s '^[[1~' '^[[H'  # Home
bindkey -s '^[[4~' '^[[F'  # End

autoload -Uz up-line-or-beginning-search
autoload -Uz down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search

bindkey '^?'      backward-delete-char           # Backspace
bindkey '^[[3~'   delete-char                    # Delete
bindkey '^[[H'    beginning-of-line              # Home
bindkey '^[[F'    end-of-line                    # End
bindkey '^[[1;5C' forward-word                   # Ctrl+Right
bindkey '^[[1;5D' backward-word                  # Ctrl+Left
bindkey '^H'      backward-kill-word             # Ctrl+Backspace
bindkey '^[[3;5~' kill-word                      # Ctrl+Del
bindkey '^[[D'    backward-char                  # Left
bindkey '^[[C'    forward-char                   # Right
bindkey '^[[A'    up-line-or-beginning-search    # Up
bindkey '^[[B'    down-line-or-beginning-search  # Down
bindkey '^[[5~'   history-search-backward        # Page Up
bindkey '^[[6~'   history-search-forward         # Page Down
