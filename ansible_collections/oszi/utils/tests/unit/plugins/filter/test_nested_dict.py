# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring,no-name-in-module,redefined-outer-name
import copy

import pytest

from ansible.errors import AnsibleError
from ansible_collections.oszi.utils.plugins.filter.nested_dict import (
    list_to_nested_dict,
    nested_dict_to_list,
    unique_nested_list,
    update_nested_dict,
)


def test_nested_dict_to_list_adds_key_attribute_in_order():
    input_dict = {"b": {"x": 1}, "a": {"x": 2}}
    assert nested_dict_to_list(input_dict, "name") == [{"x": 1, "name": "b"}, {"x": 2, "name": "a"}]


def test_nested_dict_to_list_keeps_matching_key_attribute():
    assert nested_dict_to_list({"a": {"name": "a", "x": 1}}, "name") == [{"name": "a", "x": 1}]


def test_nested_dict_to_list_does_not_mutate_input():
    input_dict = {"a": {"x": 1}}
    expected = copy.deepcopy(input_dict)
    nested_dict_to_list(input_dict, "name")
    assert input_dict == expected


def test_nested_dict_to_list_empty():
    assert not nested_dict_to_list({}, "name")


def test_nested_dict_to_list_mismatched_key_attribute():
    with pytest.raises(ValueError, match="does not match"):
        nested_dict_to_list({"a": {"name": "b"}}, "name")


@pytest.mark.parametrize("input_dict", [[], "a", None, {"a": "x"}, {"a": [{"name": "a"}]}])
def test_nested_dict_to_list_type_errors(input_dict):
    with pytest.raises(TypeError):
        nested_dict_to_list(input_dict, "name")


def test_list_to_nested_dict():
    input_list = [{"name": "b", "x": 1}, {"name": "a", "x": 2}]
    assert list_to_nested_dict(input_list, "name") == {"b": {"name": "b", "x": 1}, "a": {"name": "a", "x": 2}}
    assert list(list_to_nested_dict(input_list, "name")) == ["b", "a"]


def test_list_to_nested_dict_remove_key_does_not_mutate_input():
    input_list = [{"name": "a", "x": 1}]
    expected = copy.deepcopy(input_list)
    assert list_to_nested_dict(input_list, "name", remove_key=True) == {"a": {"x": 1}}
    assert input_list == expected


def test_list_to_nested_dict_missing_key_attribute():
    with pytest.raises(KeyError):
        list_to_nested_dict([{"x": 1}], "name")


def test_list_to_nested_dict_duplicate_key():
    with pytest.raises(ValueError, match="not unique"):
        list_to_nested_dict([{"name": "a"}, {"name": "a"}], "name")


@pytest.mark.parametrize("input_list", [{}, "a", None, ["a"], [[{"name": "a"}]]])
def test_list_to_nested_dict_type_errors(input_list):
    with pytest.raises(TypeError):
        list_to_nested_dict(input_list, "name")


def test_round_trip():
    input_dict = {"b": {"x": 1}, "a": {"x": 2}}
    as_list = nested_dict_to_list(input_dict, "name")
    assert list_to_nested_dict(as_list, "name", remove_key=True) == input_dict


def test_unique_nested_list_preserves_order():
    input_list = [{"name": "b"}, {"name": "a"}]
    assert unique_nested_list(input_list, "name") == input_list


def test_unique_nested_list_rejects_duplicates():
    # Duplicates are an error, not deduplicated.
    with pytest.raises(ValueError, match="not unique"):
        unique_nested_list([{"name": "a", "x": 1}, {"name": "a", "x": 2}], "name")


def test_update_nested_dict_creates_and_updates_elements():
    input_dict = {"a": {"x": 1}}
    assert update_nested_dict(input_dict, {"a": 2, "b": 3}, "y") == {"a": {"x": 1, "y": 2}, "b": {"y": 3}}


def test_update_nested_dict_does_not_mutate_input():
    input_dict = {"a": {"x": 1}}
    expected = copy.deepcopy(input_dict)
    update_nested_dict(input_dict, {"a": 2}, "y")
    assert input_dict == expected


@pytest.mark.parametrize(
    "input_dict, new_values",
    [([], {}), ({}, []), ({"a": "x"}, {"a": 1}), (None, {})],
)
def test_update_nested_dict_type_errors(input_dict, new_values):
    with pytest.raises(TypeError):
        update_nested_dict(input_dict, new_values, "y")


def test_readme_quadlets_chain(template):
    expression = """{{ {} | oszi.utils.update_nested_dict(quadlets, 'quadlet')
        | oszi.utils.update_nested_dict(files, 'files')
        | oszi.utils.nested_dict_to_list('name') }}"""
    result = template(
        expression,
        quadlets={"web": {"Container": {}}, "db": {"Container": {}}},
        files={"web": ["a.conf"]},
    )
    assert result == [
        {"quadlet": {"Container": {}}, "files": ["a.conf"], "name": "web"},
        {"quadlet": {"Container": {}}, "name": "db"},
    ]


def test_template_round_trip(template):
    expression = "{{ items | oszi.utils.unique_nested_list('name') | oszi.utils.list_to_nested_dict('name', true) }}"
    assert template(expression, items=[{"name": "a", "x": 1}]) == {"a": {"x": 1}}


def test_template_error(template):
    with pytest.raises(AnsibleError, match="does not match"):
        template("{{ {'a': {'name': 'b'}} | oszi.utils.nested_dict_to_list('name') }}")
