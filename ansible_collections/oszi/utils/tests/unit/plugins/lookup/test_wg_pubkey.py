# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring,no-name-in-module,redefined-outer-name
import base64
import sys
from subprocess import CalledProcessError

import pytest

from ansible.errors import AnsibleError
from ansible.plugins.loader import lookup_loader

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


@pytest.fixture
def fake_wg(lookup, mocker):
    # Stands in for `wg pubkey`: knows only the RFC 7748 key pair and fails on anything else.
    def check_output(cmd, *, text, input):  # pylint: disable=redefined-builtin
        assert cmd == ["wg", "pubkey"] and text
        if input != RFC7748_PRIVATE_KEY:
            raise CalledProcessError(1, cmd, output="", stderr="Key is not the correct length or format\n")
        return RFC7748_PUBLIC_KEY + "\n"

    module = sys.modules[type(lookup).__module__]
    return mocker.patch.object(module, "check_output", side_effect=check_output)


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


@pytest.mark.usefixtures("fake_wg")
def test_wg_pubkey_rfc7748(lookup):
    assert lookup.run([RFC7748_PRIVATE_KEY]) == [RFC7748_PUBLIC_KEY]


@pytest.mark.usefixtures("fake_wg")
@pytest.mark.parametrize("private_key", ["", "invalid", RFC7748_PRIVATE_KEY[:-4]])
def test_wg_pubkey_invalid_key(lookup, private_key):
    with pytest.raises(AnsibleError, match="returned non-zero exit status") as excinfo:
        lookup.run([private_key])
    if private_key:
        assert private_key not in error_chain_text(excinfo.value)


@pytest.mark.usefixtures("fake_wg")
def test_template(template):
    assert template("{{ lookup('oszi.utils.wg_pubkey', key) }}", key=RFC7748_PRIVATE_KEY) == RFC7748_PUBLIC_KEY
