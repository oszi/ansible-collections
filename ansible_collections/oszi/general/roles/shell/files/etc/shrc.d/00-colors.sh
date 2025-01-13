# shellcheck shell=sh
# RedHat/Fedora makes every shell a login shell
# and sources /etc/profile.d/color*.sh

if [ -z "${LS_COLORS-}" ] && command -v dircolors >/dev/null 2>&1; then
    # shellcheck disable=SC2015 # if-then-else
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
fi

for grep in grep egrep fgrep xzgrep xzegrep xzfgrep zgrep zegrep zfgrep; do
    if ! alias "$grep" >/dev/null 2>&1 && command -v "$grep" >/dev/null 2>&1; then
        # shellcheck disable=SC2139 # expand when defined
        alias "${grep}=${grep} --color=auto"
    fi
done
unset grep

if [ -n "${ZSH_VERSION-}" ]; then
    autoload -Uz +X colors && colors
fi
