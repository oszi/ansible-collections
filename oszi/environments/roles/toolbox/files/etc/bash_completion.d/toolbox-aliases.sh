if command -v kubectl >/dev/null 2>&1; then
  _completion_loader kubectl
  complete -o default -F __start_kubectl k
fi

if command -v kubectx >/dev/null 2>&1; then
  _completion_loader kubectx
  _completion_loader kubens
  complete -F _kube_contexts kctx
  complete -F _kube_namespaces kns
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
