# shellcheck shell=sh disable=SC3044 # in POSIX complete is undefined

# Abort immediately if completion is not supported.
if ! type complete >/dev/null 2>&1; then
    return
fi

if command -v tofu >/dev/null 2>&1; then
    complete -C tofu tofu
fi

if command -v terraform >/dev/null 2>&1; then
    complete -C terraform terraform
    complete -C terraform tf
elif command -v tofu >/dev/null 2>&1; then
    complete -C tofu tf
fi

if (command -v aws && command -v aws_completer) >/dev/null 2>&1; then
    complete -C "$(command -v aws_completer)" aws
fi

# _completion_loader is only defined in bash // ZSH auto completes aliases.
if ! type _completion_loader >/dev/null 2>&1; then
    return
fi

if command -v git >/dev/null 2>&1; then
    _completion_loader git
    complete -o bashdefault -o default -o nospace -F __git_wrap__git_main g
fi

if command -v kubectl >/dev/null 2>&1; then
    _completion_loader kubectl
    complete -o default -F __start_kubectl k
fi
