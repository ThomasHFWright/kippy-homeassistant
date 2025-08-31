from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def build_device_info(pet_id: int | str, pet: dict[str, Any], name: str) -> DeviceInfo:
    """Create a DeviceInfo object for a Kippy pet with IDs and IMEI."""
    identifiers: set[tuple[str, str]] = {(DOMAIN, str(pet_id))}
    connections: set[tuple[str, str]] = set()

    kippy_id = pet.get("kippyID") or pet.get("kippy_id")
    if kippy_id:
        identifiers.add((DOMAIN, str(kippy_id)))
        connections.add(("kippy_id", str(kippy_id)))

    kippy_imei = pet.get("kippyIMEI")
    if kippy_imei:
        identifiers.add((DOMAIN, str(kippy_imei)))
        connections.add(("imei", str(kippy_imei)))

    return DeviceInfo(
        identifiers=identifiers,
        connections=connections or None,
        name=name,
        manufacturer="Kippy",
        model=pet.get("kippyType"),
        sw_version=pet.get("kippyFirmware"),
        serial_number=pet.get("kippySerial"),
    )
