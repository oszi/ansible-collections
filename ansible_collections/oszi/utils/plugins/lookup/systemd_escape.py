# pylint: disable=missing-class-docstring,missing-function-docstring,missing-module-docstring,line-too-long
from subprocess import check_output, CalledProcessError

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

DOCUMENTATION = r"""
name: systemd_escape
author: "David O. (oszi.dev)"
version_added: "4.0"
short_description: A simple wrapper around systemd-escape.
description:
    - A simple wrapper around systemd-escape.
options:
    _terms:
        description: String(s) to escape.
        required: True
    suffix:
        description: >-
           Appends the specified unit type suffix to the escaped string. Takes one of the unit types supported by
           systemd, such as "service" or "mount". May not be used in conjunction with --template=, --unescape or
           --mangle.
        type: string
        required: False
    template:
        description: >-
           Inserts the escaped strings in a unit name template. Takes a unit name template such as foobar@.service.
           With --unescape, expects instantiated unit names for this template and extracts and unescapes just the
           instance part. May not be used in conjunction with --suffix=, --instance or --mangle.
        type: string
        required: False
    path:
        description: >-
           When escaping or unescaping a string, assume it refers to a file system path. This simplifies the path
           (leading, trailing, and duplicate "/" characters are removed, no-op path "." components are removed, and
           for absolute paths, leading ".."  components are removed). After the simplification, the path must not
           contain "..". This is particularly useful for generating strings suitable for unescaping with the "%f"
           specifier in unit files.
        type: boolean
        required: False
    unescape:
        description: >-
           Instead of escaping the specified strings, undo the escaping, reversing the operation. May not be used in
           conjunction with --suffix= or --mangle.
        type: boolean
        required: False
    mangle:
        description: >-
           Like --escape, but only escape characters that are obviously not escaped yet, and possibly automatically
           append an appropriate unit type suffix to the string. May not be used in conjunction with --suffix=,
           --template= or --unescape.
        type: boolean
        required: False
    instance:
        description: >-
            With --unescape, unescape and print only the instance part of an instantiated unit name template. Results
            in an error for an uninstantiated template like ssh@.service or a non-template name like ssh.service. Must
            be used in conjunction with --unescape and may not be used in conjunction with --template.
        type: boolean
        required: False
"""

display = Display()


# pylint: disable=too-few-public-methods
class LookupModule(LookupBase):
    FLAG_OPTIONS = [
        "path",
        "unescape",
    ]

    KEY_VALUE_OPTIONS = [
        "suffix",
        "template",
        "mangle",
        "instance",
    ]

    def run(self, terms, variables=None, **kwargs):
        self.set_options(var_options=variables, direct=kwargs)

        ret = []
        cmd_args = []

        for option in self.FLAG_OPTIONS:
            if self.get_option(option):
                cmd_args.append(f"--{option}")

        for option in self.KEY_VALUE_OPTIONS:
            value = self.get_option(option)
            if value is not None:
                cmd_args.append(f"--{option}={value}")

        for term in terms:
            command = ["systemd-escape", *cmd_args, term]
            try:
                term_escaped = check_output(command).rstrip()
                ret.append(term_escaped)
            except CalledProcessError as e:
                raise AnsibleError(f"{command} returned non-zero exit status") from e
            except FileNotFoundError as e:
                raise AnsibleError("systemd-escape is not installed") from e

        return ret
