# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,line-too-long
# black -l 120 --target-version=py311 ansible_collections/oszi/general/plugins/filter/nested_dict.py
from typing import Any, Dict, List, TypeVar

_KeyT = TypeVar("_KeyT")
NestedDict = Dict[_KeyT, Dict[_KeyT, Any]]
NestedList = List[Dict[_KeyT, Any]]


def nested_dict_to_list(input_dict: NestedDict, key_attribute: _KeyT) -> NestedList:
    if not isinstance(input_dict, dict):
        raise TypeError("Input variable is not a dictionary")

    result = []
    for element_key, element in input_dict.items():
        if not isinstance(element, dict):
            raise TypeError("Input variable element is not a dictionary")

        if key_attribute not in element:
            element = element.copy()
            element[key_attribute] = element_key
        elif element[key_attribute] != element_key:
            raise ValueError("Input variable element key attribute does not match")

        result.append(element)
    return result


def list_to_nested_dict(input_list: NestedList, key_attribute: _KeyT, remove_key: bool = False) -> NestedDict:
    if not isinstance(input_list, list):
        raise TypeError("Input variable is not a list")

    result = {}
    for element in input_list:
        if not isinstance(element, dict):
            raise TypeError("Input variable element is not a dictionary")
        if key_attribute not in element:
            raise KeyError("Input variable element key attribute is missing")

        element_key = element[key_attribute]
        if element_key in result:
            raise ValueError("Input variable element key is not unique")

        if remove_key:
            element = element.copy()
            del element[key_attribute]

        result[element_key] = element
    return result


def unique_nested_list(input_list: NestedList, key_attribute: _KeyT) -> NestedList:
    # Ensure uniqueness by converting to a dictionary
    nested_dict = list_to_nested_dict(input_list, key_attribute, remove_key=False)
    return list(nested_dict.values())


def update_nested_dict(input_dict: NestedDict, new_values: Dict[_KeyT, Any], new_attribute: _KeyT) -> NestedDict:
    if not isinstance(input_dict, dict):
        raise TypeError("Input variable is not a dictionary")
    if not isinstance(new_values, dict):
        raise TypeError("New values is not a dictionary")

    result = input_dict.copy()
    for element_key, value in new_values.items():
        if element_key not in result:
            result[element_key] = {}
        elif not isinstance(result[element_key], dict):
            raise TypeError("Input variable element is not a dictionary")
        else:
            result[element_key] = result[element_key].copy()

        result[element_key][new_attribute] = value
    return result


# pylint: disable=too-few-public-methods
class FilterModule:
    def filters(self):
        return {
            "nested_dict_to_list": nested_dict_to_list,
            "list_to_nested_dict": list_to_nested_dict,
            "unique_nested_list": unique_nested_list,
            "update_nested_dict": update_nested_dict,
        }
