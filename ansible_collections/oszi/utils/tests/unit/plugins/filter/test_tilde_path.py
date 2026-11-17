# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring,no-name-in-module
import subprocess

import pytest

from ansible.errors import AnsibleError
from ansible_collections.oszi.utils.plugins.filter.tilde_path import (
    absolute_to_quoted_tilde_path,
    absolute_to_tilde_path,
    home_var_to_quoted_tilde_path,
    home_var_to_tilde_path,
    quote_tilde_path,
    tilde_to_absolute_path,
)

HOME = "/home/alice"


@pytest.mark.parametrize(
    "path, home, user, expected",
    [
        ("/home/alice", HOME, "", "~"),
        ("/home/alice/", HOME, "", "~/"),
        ("/home/alice/x", HOME, "", "~/x"),
        ("/home/alice/x/", "/home/alice/", "", "~/x/"),
        ("/home/alice/./a/../b", HOME, "", "~/b"),
        ("/home/alice/x", HOME, "alice", "~alice/x"),
        ("/", "/", "", "~/"),
        # Unchanged, no path component boundary or not under home.
        ("/home/alice2", HOME, "", "/home/alice2"),
        ("/home/bob/x", HOME, "", "/home/bob/x"),
        ("//home/alice/x", HOME, "", "//home/alice/x"),
        ("/etc", "/", "", "/etc"),
    ],
)
def test_absolute_to_tilde_path(path, home, user, expected):
    assert absolute_to_tilde_path(path, home, user) == expected


@pytest.mark.parametrize(
    "path, home, user",
    [
        ("x", HOME, ""),
        ("~/x", HOME, ""),
        (None, HOME, ""),
        ("/x", "home", ""),
        ("/x", None, ""),
        ("/x", HOME, "-alice"),
        ("/x", HOME, "al ice"),
        ("/x", HOME, "a/b"),
        ("/x", HOME, None),
    ],
)
def test_absolute_to_tilde_path_value_errors(path, home, user):
    with pytest.raises(ValueError):
        absolute_to_tilde_path(path, home, user)


@pytest.mark.parametrize(
    "path, user, expected",
    [
        ("$HOME", "", "~"),
        ("${HOME}", "", "~"),
        ("$HOME/x", "", "~/x"),
        ("${HOME}/x", "", "~/x"),
        ('"$HOME"', "", "~"),
        ('"$HOME/x"', "", "~/x"),
        ('"${HOME}/x"', "", "~/x"),
        ('"$HOME/a"/b', "", "~/a/b"),
        ("$HOME/x", "alice", "~alice/x"),
        # The remainder is taken literally, also within double quotes.
        ('"$HOME/$x"', "", "~/$x"),
        # Unchanged, not $HOME or no path component boundary.
        ("$HOMEDIR/x", "", "$HOMEDIR/x"),
        ("$HOME_X", "", "$HOME_X"),
        ("$HOME-x", "", "$HOME-x"),
        ("${HOME}x", "", "${HOME}x"),
        ('"$HOME"x', "", '"$HOME"x'),
        ('"$HOME/a\\"b"', "", '"$HOME/a\\"b"'),
        ("~/x", "", "~/x"),
        ("/x", "", "/x"),
        ("", "", ""),
    ],
)
def test_home_var_to_tilde_path(path, user, expected):
    assert home_var_to_tilde_path(path, user) == expected


@pytest.mark.parametrize("path, user", [(None, ""), ("$HOME", "-alice"), ("$HOME", None)])
def test_home_var_to_tilde_path_value_errors(path, user):
    with pytest.raises(ValueError):
        home_var_to_tilde_path(path, user)


@pytest.mark.parametrize(
    "path, home, user, expected",
    [
        ("~", HOME, "", "/home/alice"),
        ("~/", HOME, "", "/home/alice/"),
        ("~/x", HOME, "", "/home/alice/x"),
        ("~/x", "/home/alice/", "", "/home/alice/x"),
        ("~/x", HOME, "alice", "/home/alice/x"),
        ("~alice/x", HOME, "alice", "/home/alice/x"),
        ("~", "/", "", "/"),
        ("~/x", "/", "", "/x"),
    ],
)
def test_tilde_to_absolute_path(path, home, user, expected):
    assert tilde_to_absolute_path(path, home, user) == expected


@pytest.mark.parametrize(
    "path, home, user, match",
    [
        ("/x", HOME, "", "not a tilde path"),
        ("x", HOME, "", "not a tilde path"),
        (None, HOME, "", "not a tilde path"),
        ("~/x", "home", "", "not an absolute path"),
        ("~/x", HOME, "-alice", "not a valid username"),
        ("~bob/x", HOME, "alice", "do not match"),
        ("~bob/x", HOME, "", "unknown user"),
    ],
)
def test_tilde_to_absolute_path_value_errors(path, home, user, match):
    with pytest.raises(ValueError, match=match):
        tilde_to_absolute_path(path, home, user)


@pytest.mark.parametrize(
    "path, expected",
    [
        ("~", "~"),
        ("~/", "~/"),
        ("~/x", "~/x"),
        ("~/a b", "~/'a b'"),
        ("~/a/b c/", "~/'a/b c/'"),
        ("~alice", "~alice"),
        ("~al ice/x", "~'al ice'/x"),
        ("/a b", "'/a b'"),
        ("a", "a"),
        ("", "''"),
        ("~/$(id)", "~/'$(id)'"),
        ("~/`id`", "~/'`id`'"),
        ("~/a;b", "~/'a;b'"),
    ],
)
def test_quote_tilde_path(path, expected):
    assert quote_tilde_path(path) == expected


def test_quote_tilde_path_value_error():
    with pytest.raises(ValueError):
        quote_tilde_path(None)


SHELL_HOME = "/h"

# Paths whose shell expansion must equal tilde_to_absolute_path, or the literal path if not tilde-expandable.
SHELL_ROUND_TRIP_PATHS = [
    "~",
    "~/",
    "~/x",
    "~/a b",
    "~/a/b c/",
    "~/$(id)",
    "~/`id`",
    "~/${HOME}",
    "~/a;b",
    "~/a|b&c",
    "~/'",
    '~/"',
    "~/\\",
    "~/a\nb",
    "~/*",
    "~/-x",
    "~al ice/x",
    "~$(id)/x",
    "/a b",
    "$(id)",
    "-x",
    "",
]


@pytest.mark.parametrize("path", SHELL_ROUND_TRIP_PATHS)
def test_quote_tilde_path_shell_round_trip(path):
    quoted = quote_tilde_path(path)
    result = subprocess.run(
        ["bash", "--norc", "--noprofile", "-c", f"printf %s {quoted}"],
        check=True,
        capture_output=True,
        text=True,
        env={"HOME": SHELL_HOME, "PATH": "/usr/bin:/bin"},
    )
    if path == "~" or path.startswith("~/"):
        expected = tilde_to_absolute_path(path, SHELL_HOME)
    else:
        expected = path
    assert result.stdout == expected
    assert not result.stderr


def test_absolute_to_quoted_tilde_path():
    assert absolute_to_quoted_tilde_path("/home/alice/a b", HOME) == "~/'a b'"
    assert absolute_to_quoted_tilde_path("/home/alice/x", HOME, "alice") == "~alice/x"
    assert absolute_to_quoted_tilde_path("/srv/a b", HOME) == "'/srv/a b'"


def test_home_var_to_quoted_tilde_path():
    assert home_var_to_quoted_tilde_path('"$HOME/a b"') == "~/'a b'"
    assert home_var_to_quoted_tilde_path("$HOME/x", "alice") == "~alice/x"
    assert home_var_to_quoted_tilde_path("$HOMEDIR") == "'$HOMEDIR'"


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("{{ '/home/alice/x' | oszi.utils.absolute_to_tilde_path(home) }}", "~/x"),
        ("{{ '/home/alice/a b' | oszi.utils.absolute_to_quoted_tilde_path(home) }}", "~/'a b'"),
        ("{{ '\"$HOME/.config\"' | oszi.utils.home_var_to_tilde_path }}", "~/.config"),
        ("{{ '\"$HOME/.config\"' | oszi.utils.home_var_to_quoted_tilde_path }}", "~/.config"),
        ("{{ '~/a b' | oszi.utils.tilde_to_absolute_path(home) }}", "/home/alice/a b"),
        ("{{ '~/.config' | oszi.utils.quote_tilde_path }}", "~/.config"),
    ],
)
def test_template(template, expression, expected):
    assert template(expression, home=HOME) == expected


def test_template_error(template):
    with pytest.raises(AnsibleError, match="not a tilde path"):
        template("{{ '/x' | oszi.utils.tilde_to_absolute_path(home) }}", home=HOME)
