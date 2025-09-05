from custom_components.kippy.api import _return_code_error, _treat_401_as_success
from custom_components.kippy.const import RETURN_VALUES


def test_return_code_unauthorized_not_success():
    assert not _treat_401_as_success("/path", {"return": RETURN_VALUES.UNAUTHORIZED})


def test_return_code_invalid_credentials_not_success():
    assert not _treat_401_as_success(
        "/path", {"return": RETURN_VALUES.INVALID_CREDENTIALS}
    )


def test_return_code_malformed_request_not_success():
    assert not _treat_401_as_success(
        "/path", {"return": RETURN_VALUES.MALFORMED_REQUEST}
    )


def test_error_message_for_unknown_code():
    assert _return_code_error(999) == "Unknown error code 999"


def test_error_message_for_known_code():
    assert (
        _return_code_error(RETURN_VALUES.INVALID_CREDENTIALS)
        == "Invalid credentials (code 108)"
    )
