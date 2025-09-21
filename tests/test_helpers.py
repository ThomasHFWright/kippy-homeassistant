from custom_components.kippy.const import DOMAIN
from custom_components.kippy.helpers import (
    build_device_info,
    normalize_kippy_identifier,
)


def test_build_device_info_with_ids() -> None:
    """Ensure identifiers use pet ID and connections include device info."""
    pet = {
        "kippyID": 123,
        "kippyIMEI": "imei",
        "kippyType": "type",
        "kippyFirmware": "1",
        "kippySerial": "serial",
    }
    info = build_device_info(1, pet, "Name")
    assert info["identifiers"] == {(DOMAIN, "1")}
    assert ("kippy_id", "123") in info["connections"]
    assert ("imei", "imei") in info["connections"]
    assert ("serial", "serial") in info["connections"]
    assert info["name"] == "Name"
    assert info["model"] == "type"
    assert info["sw_version"] == "1"
    assert info["serial_number"] == "serial"


def test_build_device_info_without_ids() -> None:
    """Ensure missing optional fields result in minimal device info."""
    pet = {}
    info = build_device_info(2, pet, "Name")
    assert info.get("connections") is None
    assert info.get("model") is None


def test_normalize_kippy_identifier_falls_back_to_pet_id() -> None:
    """Pet ID should be used when explicit Kippy IDs are missing."""

    assert normalize_kippy_identifier({"petID": "42"}, include_pet_id=True) == 42


def test_normalize_kippy_identifier_invalid_values() -> None:
    """Non-numeric identifiers should be ignored."""

    assert normalize_kippy_identifier({"kippyID": "abc"}) is None
    assert normalize_kippy_identifier({"petID": "7"}) is None
