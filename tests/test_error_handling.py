from custom_components.kippy.api import _treat_401_as_success
from custom_components.kippy.const import RETURN_VALUES


def test_return_code_unauthorized_not_success():
    assert not _treat_401_as_success("/path", {"return": RETURN_VALUES.UNAUTHORIZED})


def test_return_code_invalid_credentials_not_success():
    assert not _treat_401_as_success(
        "/path", {"return": RETURN_VALUES.INVALID_CREDENTIALS}
    )
