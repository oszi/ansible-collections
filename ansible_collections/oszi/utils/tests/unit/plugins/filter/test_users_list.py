# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring,no-name-in-module
import pytest

from ansible_collections.oszi.utils.plugins.filter.users_list import (
    is_login_user,
    login_users_list,
    non_login_users_list,
)

USERS = [
    {"name": "root", "home": "/root", "shell": "/bin/bash"},
    {"name": "alice", "home": "/home/alice", "shell": "/bin/zsh"},
    {"name": "bob"},
    {"name": "svc", "system": True},
    {"name": "nologin", "shell": "/usr/sbin/nologin"},
    {"name": "gone", "state": "absent"},
    {"name": "gone_svc", "state": "absent", "system": True},
]


@pytest.mark.parametrize(
    "user",
    [
        {},
        {"name": "alice", "home": "/home/alice", "shell": "/bin/bash"},
        {"shell": ""},
        {"home": "/nonexistent/alice"},
        {"system": False},
        {"system": "no"},
        # Invalid values of "system" are ignored.
        {"system": "maybe"},
    ],
)
def test_is_login_user_true(user):
    assert is_login_user(user) is True


@pytest.mark.parametrize(
    "user",
    [
        {"system": True},
        {"system": "yes"},
        {"system": "true"},
        {"system": 1},
        {"shell": "nologin"},
        {"shell": "/usr/sbin/nologin"},
        {"shell": "/bin/false"},
        {"shell": "/bin/true"},
        {"home": "/"},
        {"home": "//"},
        {"home": "/bin"},
        {"home": "/sbin/"},
        {"home": "/home/../bin"},
        {"home": "/nonexistent"},
    ],
)
def test_is_login_user_false(user):
    assert is_login_user(user) is False


@pytest.mark.parametrize("user", [None, "alice", ["alice"]])
def test_is_login_user_type_error(user):
    with pytest.raises(TypeError):
        is_login_user(user)


def test_login_users_list():
    assert [user["name"] for user in login_users_list(USERS)] == ["root", "alice", "bob"]


def test_non_login_users_list():
    assert [user["name"] for user in non_login_users_list(USERS)] == ["svc", "nologin"]


def test_users_lists_partition_present_users():
    login, non_login = login_users_list(USERS), non_login_users_list(USERS)
    present = [user for user in USERS if user.get("state", "present") == "present"]
    assert sorted(user["name"] for user in login + non_login) == sorted(user["name"] for user in present)
    assert not [user for user in login if user in non_login]


@pytest.mark.parametrize("users_list", [None, {}, "alice", ["alice"], [None]])
@pytest.mark.parametrize("users_filter", [login_users_list, non_login_users_list])
def test_users_list_type_errors(users_filter, users_list):
    with pytest.raises(TypeError):
        users_filter(users_list)


def test_readme_gnome_users(template):
    expression = """{{ users_list | default([]) | oszi.utils.login_users_list
        | map(attribute='name') | reject('equalto', 'root') | list }}"""
    assert template(expression, users_list=USERS) == ["alice", "bob"]
    assert template(expression) == []


def test_template_non_login_users_list(template):
    assert template("{{ users | oszi.utils.non_login_users_list | length }}", users=USERS) == 2
    assert template("{{ user | oszi.utils.is_login_user }}", user=USERS[1]) is True
