# pylint: disable=missing-class-docstring,missing-module-docstring
# black -l 120 --target-version=py311 ansible_collections/oszi/general/plugins/lookup/wg_pubkey.py
from functools import partial
from subprocess import check_output, CalledProcessError

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

DOCUMENTATION = r"""
name: wg_pubkey
author: "David O. (oszi.dev)"
version_added: "3.5"
short_description: Generate wireguard public keys from private keys.
description:
    - Generate wireguard public keys from private keys.
options:
_terms:
    description: private key(s)
    required: True
"""

display = Display()


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        self.set_options(var_options=variables, direct=kwargs)
        check_output_wg_pubkey = partial(check_output, ["wg", "pubkey"], text=True)

        ret = []
        for term in terms:
            try:
                pubkey = check_output_wg_pubkey(input=term).strip()
                ret.append(pubkey)
            except CalledProcessError as e:
                raise AnsibleError("Command 'wg pubkey' returned non-zero exit status") from e
            except FileNotFoundError as e:
                raise AnsibleError("wireguard-tools is not installed") from e

        return ret
