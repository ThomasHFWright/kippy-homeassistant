# pylint: disable=missing-function-docstring

"""Tests for API error-handling helpers."""

from custom_components.kippy.api import _return_code_error, _treat_401_as_success
from custom_components.kippy.const import RETURN_VALUES


def test_return_code_malformed_request_not_success():
    for code in RETURN_VALUES.MALFORMED_REQUEST:
        assert not _treat_401_as_success("/path", {"return": code})


def test_return_code_invalid_credentials_not_success():
    assert not _treat_401_as_success(
        "/path", {"return": RETURN_VALUES.INVALID_CREDENTIALS}
    )


def test_return_code_subscription_failure_not_success():
    assert not _treat_401_as_success(
        "/path", {"return": RETURN_VALUES.SUBSCRIPTION_FAILURE}
    )


def test_return_code_success_string():
    assert _treat_401_as_success("/path", {"return": "0"})


def test_return_code_invalid_credentials_string_not_success():
    assert not _treat_401_as_success("/path", {"return": "108"})


def test_error_message_for_unknown_code():
    assert _return_code_error(999) == "Unknown error code 999"


def test_error_message_for_known_code():
    assert (
        _return_code_error(RETURN_VALUES.INVALID_CREDENTIALS)
        == "Invalid credentials (code 108)"
    )


def test_error_message_for_malformed_request():
    for code in RETURN_VALUES.MALFORMED_REQUEST:
        assert _return_code_error(code) == f"Malformed request (code {code})"


def test_error_message_for_authorization_expired():
    assert (
        _return_code_error(RETURN_VALUES.AUTHORIZATION_EXPIRED)
        == "Authorization expired (code 6)"
    )


def test_error_message_for_subscription_failure():
    assert (
        _return_code_error(RETURN_VALUES.SUBSCRIPTION_FAILURE)
        == "Subscription inactive (code False)"
    )
