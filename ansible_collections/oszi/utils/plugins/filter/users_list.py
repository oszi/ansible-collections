# pylint: disable=missing-class-docstring,missing-function-docstring,missing-module-docstring
from posixpath import normpath, sep as SEP
from typing import Any, Dict, List

from ansible.module_utils.parsing.convert_bool import boolean

# List of dictionaries for ansible.builtin.user, see oszi.general.users
NestedList = List[Dict[str, Any]]

NOLOGIN_SUFFIXES = (f"{SEP}nologin", f"{SEP}false")


# Supports output of ansible.builtin.user as input.
def is_login_user(user: Dict[str, Any]) -> bool:
    if not isinstance(user, dict):
        raise TypeError("Input variable 'user' is not a dictionary")

    # ansible.builtin.user omits "system" for existing users.
    if boolean(user.get("system", False), strict=False):
        return False

    if (shell := user.get("shell")) is not None:
        if shell.endswith(NOLOGIN_SUFFIXES):
            return False

    if (home := user.get("home")) is not None:
        if normpath(home).strip(SEP) == "":
            return False

    return True


def _filter_users_list(users_list: NestedList, is_login: bool) -> NestedList:
    if not isinstance(users_list, list):
        raise TypeError("Input variable 'users_list' is not a list")

    result = []
    for user in users_list:
        if not isinstance(user, dict):
            raise TypeError("Input variable element of 'users_list' is not a dictionary")

        if user.get("state", "present") == "present":
            if is_login_user(user) == is_login:
                result.append(user)

    return result


def login_users_list(users_list: NestedList) -> NestedList:
    return _filter_users_list(users_list, is_login=True)


def non_login_users_list(users_list: NestedList) -> NestedList:
    return _filter_users_list(users_list, is_login=False)


# pylint: disable=too-few-public-methods
class FilterModule:
    def filters(self):
        return {
            "is_login_user": is_login_user,
            "login_users_list": login_users_list,
            "non_login_users_list": non_login_users_list,
        }
