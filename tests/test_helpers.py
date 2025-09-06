from custom_components.kippy.const import DOMAIN
from custom_components.kippy.helpers import build_device_info


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
