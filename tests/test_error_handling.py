from custom_components.kippy.api import _treat_401_as_success


def test_return_code_113_not_success():
    assert not _treat_401_as_success("/path", {"return": "113"})
