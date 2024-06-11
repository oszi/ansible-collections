_completion_loader git
if type -t __git_wrap__git_main >/dev/null 2>&1; then
  complete -o bashdefault -o default -o nospace -F __git_wrap__git_main g
fi

_completion_loader ssh
if type -t _ssh >/dev/null 2>&1; then
  complete -o nospace -F _ssh ssh-forget
  complete -o nospace -F _ssh ssh-proxied
fi

_completion_loader scp
if type -t _scp >/dev/null 2>&1; then
  complete -o nospace -F _scp scp-forget
  complete -o nospace -F _scp scp-proxied
fi
