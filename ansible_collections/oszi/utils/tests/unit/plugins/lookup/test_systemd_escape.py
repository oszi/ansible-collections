# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring,no-name-in-module,redefined-outer-name
import shutil
import sys
from subprocess import CalledProcessError

import pytest

from ansible.errors import AnsibleError
from ansible.plugins.loader import lookup_loader

needs_systemd_escape = pytest.mark.skipif(shutil.which("systemd-escape") is None, reason="systemd-escape is missing")


@pytest.fixture
def lookup():
    return lookup_loader.get("oszi.utils.systemd_escape")


@pytest.fixture
def check_output(mocker, lookup):
    module = sys.modules[type(lookup).__module__]
    return mocker.patch.object(module, "check_output", side_effect=lambda command, **_: command[-1] + "-escaped\n")


@pytest.mark.parametrize(
    "options, cmd_args",
    [
        ({}, []),
        ({"path": True}, ["--path"]),
        ({"unescape": True}, ["--unescape"]),
        ({"mangle": True}, ["--mangle"]),
        ({"unescape": True, "instance": True}, ["--unescape", "--instance"]),
        ({"suffix": "mount"}, ["--suffix=mount"]),
        ({"template": "foo@.service"}, ["--template=foo@.service"]),
        ({"path": True, "template": "foo@.service"}, ["--path", "--template=foo@.service"]),
        ({"path": False, "unescape": False, "mangle": False, "instance": False}, []),
    ],
)
def test_command(lookup, check_output, options, cmd_args):
    assert lookup.run(["a", "b"], **options) == ["a-escaped", "b-escaped"]
    assert [call.args[0] for call in check_output.call_args_list] == [
        ["systemd-escape", *cmd_args, "a"],
        ["systemd-escape", *cmd_args, "b"],
    ]


def test_command_error(lookup, mocker):
    module = sys.modules[type(lookup).__module__]
    mocker.patch.object(module, "check_output", side_effect=CalledProcessError(1, ["systemd-escape"]))
    with pytest.raises(AnsibleError, match="returned non-zero exit status"):
        lookup.run(["a"])


def test_command_not_found(lookup, mocker):
    module = sys.modules[type(lookup).__module__]
    mocker.patch.object(module, "check_output", side_effect=FileNotFoundError("systemd-escape"))
    with pytest.raises(AnsibleError, match="systemd-escape is not installed"):
        lookup.run(["a"])


@needs_systemd_escape
@pytest.mark.parametrize(
    "terms, options, expected",
    [
        (["a b", "/c"], {}, ["a\\x20b", "-c"]),
        (["/a b/c/"], {"path": True}, ["a\\x20b-c"]),
        (["/a/b"], {"path": True, "suffix": "mount"}, ["a-b.mount"]),
        (["/a/b"], {"path": True, "template": "foo@.service"}, ["foo@a-b.service"]),
        (["a-b"], {"path": True, "unescape": True}, ["/a/b"]),
        (["a b"], {"mangle": True}, ["a\\x20b.service"]),
        (["foo@a\\x20b.service"], {"unescape": True, "instance": True}, ["a b"]),
        ([], {}, []),
    ],
)
def test_systemd_escape(lookup, terms, options, expected):
    assert lookup.run(terms, **options) == expected


@needs_systemd_escape
@pytest.mark.parametrize(
    "options",
    [
        {"suffix": "mount", "template": "foo@.service"},
        {"unescape": True, "instance": True, "template": "foo@.service"},
        {"mangle": True, "suffix": "mount"},
    ],
)
def test_systemd_escape_invalid_options(lookup, options):
    with pytest.raises(AnsibleError, match="returned non-zero exit status"):
        lookup.run(["a"], **options)


@needs_systemd_escape
def test_systemd_escape_missing_instance(lookup):
    with pytest.raises(AnsibleError, match="returned non-zero exit status"):
        lookup.run(["foo.service"], unescape=True, instance=True)


@needs_systemd_escape
def test_template(template):
    readme = "{{ lookup('oszi.utils.systemd_escape', spec_path, template='podman-kube@.service') }}"
    assert template(readme, spec_path="/etc/a b.yml") == "podman-kube@-etc-a\\x20b.yml.service"
    assert template("{{ query('oszi.utils.systemd_escape', '/a', '/b', path=true) }}") == ["a", "b"]
    assert template("{{ lookup('oszi.utils.systemd_escape', 'a b', mangle=true) }}") == "a\\x20b.service"
