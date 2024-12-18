# shellcheck shell=sh disable=SC1091 # input source
# ansible managed skel

if [ -f /etc/shrc.d/.profile ]; then
    . /etc/shrc.d/.profile
fi
