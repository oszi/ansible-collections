# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# shellcheck disable=SC3010,SC3044 # in POSIX [[ ]] and shopt are undefined
# Fix VTE for non-login shells in Tilix and other terminals

if [ -n "${BASH_VERSION-}" ]; then
    if shopt -q login_shell; then
        return
    fi

elif [ -n "${ZSH_VERSION-}" ]; then
    if [[ -o login ]]; then
        return
    fi

else
    return
fi

for rc in /etc/profile.d/vte.sh /etc/profile.d/vte-2.91.sh; do
    if [ -r "$rc" ]; then
        . "$rc"
        break
    fi
done
unset rc
