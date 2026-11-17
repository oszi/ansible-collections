# pylint: disable=missing-function-docstring,missing-module-docstring
from typing import Any, Callable

import pytest

from ansible.template import Templar, trust_as_template


@pytest.fixture
def template() -> Callable[..., Any]:
    # Render an expression through real Jinja with FQCN plugin resolution, as in a playbook.
    def render(expression: str, **variables: Any) -> Any:
        return Templar(variables=variables).template(trust_as_template(expression))

    return render
