if command -v kubectl >/dev/null 2>&1; then
  alias k='kubectl'
fi

if command -v kubectx >/dev/null 2>&1; then
  alias kctx='kubectx'
  alias kns='kubens'
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
