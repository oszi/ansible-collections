# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring,no-name-in-module,redefined-outer-name
import base64
import os
import shutil
import sys
from subprocess import CalledProcessError

import pytest

from ansible.errors import AnsibleError
from ansible.plugins.loader import lookup_loader

needs_wg = pytest.mark.skipif(shutil.which("wg") is None, reason="wireguard-tools is missing")

# RFC 7748 section 6.1, Alice's X25519 key pair.
RFC7748_PRIVATE_KEY = base64.b64encode(
    bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
).decode()
RFC7748_PUBLIC_KEY = base64.b64encode(
    bytes.fromhex("8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a")
).decode()


@pytest.fixture
def lookup():
    return lookup_loader.get("oszi.utils.wg_pubkey")


def error_chain_text(err: BaseException) -> str:
    texts = []
    while err is not None:
        texts.append(str(err))
        texts.extend(str(arg) for arg in getattr(err, "args", ()))
        err = err.__cause__ or err.__context__
    return "\n".join(texts)


def test_command(lookup, mocker):
    module = sys.modules[type(lookup).__module__]
    check_output = mocker.patch.object(module, "check_output", side_effect=["pub-a\n", "pub-b \n"])
    assert lookup.run(["priv-a", "priv-b"]) == ["pub-a", "pub-b"]
    assert [call.args for call in check_output.call_args_list] == [(["wg", "pubkey"],)] * 2
    assert [call.kwargs for call in check_output.call_args_list] == [
        {"text": True, "input": "priv-a"},
        {"text": True, "input": "priv-b"},
    ]


@pytest.mark.parametrize(
    "side_effect, match",
    [
        (CalledProcessError(1, ["wg", "pubkey"]), "returned non-zero exit status"),
        (FileNotFoundError("wg"), "wireguard-tools is not installed"),
    ],
)
def test_command_errors_hide_private_key(lookup, mocker, side_effect, match):
    module = sys.modules[type(lookup).__module__]
    mocker.patch.object(module, "check_output", side_effect=side_effect)
    with pytest.raises(AnsibleError, match=match) as excinfo:
        lookup.run([RFC7748_PRIVATE_KEY])
    assert RFC7748_PRIVATE_KEY not in error_chain_text(excinfo.value)


@needs_wg
def test_wg_pubkey_rfc7748(lookup):
    assert lookup.run([RFC7748_PRIVATE_KEY]) == [RFC7748_PUBLIC_KEY]


@needs_wg
def test_wg_pubkey_matches_cryptography(lookup):
    x25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.x25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")

    private_keys = [os.urandom(32) for _index in range(8)]
    expected = [
        base64.b64encode(
            x25519.X25519PrivateKey.from_private_bytes(key)
            .public_key()
            .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode()
        for key in private_keys
    ]
    assert lookup.run([base64.b64encode(key).decode() for key in private_keys]) == expected


@needs_wg
@pytest.mark.parametrize("private_key", ["", "invalid", RFC7748_PRIVATE_KEY[:-4]])
def test_wg_pubkey_invalid_key(lookup, private_key):
    with pytest.raises(AnsibleError, match="returned non-zero exit status") as excinfo:
        lookup.run([private_key])
    if private_key:
        assert private_key not in error_chain_text(excinfo.value)


@needs_wg
def test_template(template):
    assert template("{{ lookup('oszi.utils.wg_pubkey', key) }}", key=RFC7748_PRIVATE_KEY) == RFC7748_PUBLIC_KEY
