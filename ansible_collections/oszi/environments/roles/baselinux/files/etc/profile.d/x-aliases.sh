alias e='${EDITOR:-vi}'
alias o='xdg-open'
alias g='git'

alias cp='cp -i'
alias mv='mv -i'
alias rm='rm -I'
alias xn='xargs -rd"\n"'
alias x1='xn -n1'

alias clip='xclip -i -selection clipboard'
alias gcd='cd -- "$(git rev-parse --show-toplevel)"'
alias py='$(command -v ipython3 || command -v ipython || command -v python3 || echo python)'
alias ssh-forget='ssh -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" -o "LogLevel QUIET"'
alias scp-forget='scp -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" -o "LogLevel QUIET"'

if (command -v exa || command -v eza) >/dev/null 2>&1; then
  alias l="$(command -v exa || command -v eza) -F --group-directories-first"
  alias la='l -a'
  alias ll='l -alg'
  if ! command -v tree >/dev/null 2>&1; then
    alias tree='l -T'
  fi
else
  alias l='ls -CF --group-directories-first'
  alias la='l -A'
  alias ll='l -Alh'
fi
