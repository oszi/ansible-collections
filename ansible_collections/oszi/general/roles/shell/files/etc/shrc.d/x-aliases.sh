# shellcheck shell=sh

case $- in
    *i*) ;;
      *) return ;;
esac

alias cp='cp -i'
alias mv='mv -i'
alias rm='rm -I'
alias xn='xargs -rd"\n"'
alias x1='xn -n1'
alias e='${EDITOR:-vi}'

alias py='$(command -v ipython3 || command -v ipython || command -v python3 || echo python)'
alias ssh-forget='ssh -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" -o "LogLevel QUIET"'
alias scp-forget='scp -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" -o "LogLevel QUIET"'

if (command -v eza || command -v exa) >/dev/null 2>&1; then
    # shellcheck disable=SC2139 # expand when defined
    alias l="$(command -v eza || command -v exa) -F --group-directories-first"
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

if command -v git >/dev/null 2>&1; then
    alias gcd='cd -- "$(git rev-parse --show-toplevel)"'
    alias g='git'
fi

if command -v kubectl >/dev/null 2>&1; then
    alias k='kubectl'
fi

if command -v terraform >/dev/null 2>&1; then
    if command -v tofu >/dev/null 2>&1; then
        tf() {
            if grep -Esq '\b(open)?tofu\b' .terraform.lock.hcl; then
                tofu "$@"
            else
                terraform "$@"
            fi
        }
    else
        alias tf='terraform'
    fi
elif command -v tofu >/dev/null 2>&1; then
    alias tf='tofu'
fi
