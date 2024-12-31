# shellcheck shell=sh disable=SC1091 # not following input sources

if [ -f /usr/lib/google-cloud-sdk/completion.zsh.inc ]; then
    . /usr/lib/google-cloud-sdk/completion.zsh.inc
elif [ -f /usr/lib64/google-cloud-sdk/completion.zsh.inc ]; then
    . /usr/lib64/google-cloud-sdk/completion.zsh.inc

# Fallback to bash completion with bashcompinit
elif [ -f /usr/lib/google-cloud-sdk/completion.bash.inc ]; then
    . /usr/lib/google-cloud-sdk/completion.bash.inc
elif [ -f /usr/lib64/google-cloud-sdk/completion.bash.inc ]; then
    . /usr/lib64/google-cloud-sdk/completion.bash.inc
fi
