# shellcheck shell=sh

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

bindkey '^?'      backward-delete-char           # BS          Delete one char backward
bindkey '^[[3~'   delete-char                    # Delete      Delete one char forward
bindkey '^[[H'    beginning-of-line              # Home        Go to the beginning of line
bindkey '^[[F'    end-of-line                    # End         Go to the end of line
bindkey '^[[1;5C' forward-word                   # Ctrl+Right  Go forward one word
bindkey '^[[1;5D' backward-word                  # Ctrl+Left   Go backward one word
bindkey '^H'      backward-kill-word             # Ctrl+BS     Delete previous word
bindkey '^[[3;5~' kill-word                      # Ctrl+Del    Delete next word
bindkey '^[[D'    backward-char                  # Left        Move cursor one char backward
bindkey '^[[C'    forward-char                   # Right       Move cursor one char forward
bindkey '^[[A'    up-line-or-beginning-search    # Up          Prev command in history
bindkey '^[[B'    down-line-or-beginning-search  # Down        Next command in history
bindkey '^[[5~'   history-search-backward        # Page Up     Prev command in history
bindkey '^[[6~'   history-search-forward         # Page Down   Next command in history
