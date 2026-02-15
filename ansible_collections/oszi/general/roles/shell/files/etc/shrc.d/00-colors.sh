# shellcheck shell=sh
# RedHat/Fedora makes every shell a login shell and sources /etc/profile.d/color*.sh
# The following code must be idempotent to be flexible.

if [ -z "${LS_COLORS-}" ] && command -v dircolors >/dev/null 2>&1; then
    # shellcheck disable=SC2015 # if-then-else
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
fi

for i in ls grep egrep fgrep xzgrep xzegrep xzfgrep zgrep zegrep zfgrep; do
    if ! alias "$i" >/dev/null 2>&1 && command -v "$i" >/dev/null 2>&1; then
        # shellcheck disable=SC2139 # expand when defined
        alias "${i}=${i} --color=auto"
    fi
done
unset i

if [ -n "${ZSH_VERSION-}" ]; then
    autoload -Uz +X colors && colors
fi
