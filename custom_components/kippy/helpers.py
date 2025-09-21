"""Helper utilities for the Kippy integration."""

from __future__ import annotations

from asyncio import TimeoutError as AsyncioTimeoutError
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from json import JSONDecodeError
from typing import Any, cast

from aiohttp import ClientError
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

API_EXCEPTIONS: tuple[type[Exception], ...] = (
    ClientError,
    AsyncioTimeoutError,
    RuntimeError,
    JSONDecodeError,
)


def build_device_name(pet: Mapping[str, Any], prefix: str = "Kippy") -> str:
    """Return a display name for a pet."""

    pet_name = pet.get("petName")
    return f"{prefix} {pet_name}" if pet_name else prefix


def build_device_info(
    pet_id: int | str, pet: Mapping[str, Any], name: str | None = None
) -> DeviceInfo:
    """Create a DeviceInfo object for a Kippy pet."""

    identifiers: set[tuple[str, str]] = {(DOMAIN, str(pet_id))}
    connections: set[tuple[str, str]] = set()

    kippy_id = pet.get("kippyID") or pet.get("kippy_id")
    if kippy_id:
        connections.add(("kippy_id", str(kippy_id)))

    kippy_imei = pet.get("kippyIMEI")
    if kippy_imei:
        connections.add(("imei", str(kippy_imei)))

    kippy_serial = pet.get("kippySerial")
    if kippy_serial:
        connections.add(("serial", str(kippy_serial)))

    return DeviceInfo(
        identifiers=identifiers,
        connections=connections or None,
        name=name or build_device_name(pet),
        manufacturer="Kippy",
        model=pet.get("kippyType"),
        sw_version=pet.get("kippyFirmware"),
        serial_number=kippy_serial,
    )


def is_pet_subscription_active(pet: Mapping[str, Any]) -> bool:
    """Return ``True`` if the pet's subscription is active."""

    expired_days = pet.get("expired_days")
    try:
        return int(expired_days) < 0
    except (TypeError, ValueError):
        return True


def normalize_kippy_identifier(
    pet: Mapping[str, Any], *, include_pet_id: bool = False
) -> int | None:
    """Return the numeric Kippy identifier for ``pet`` if present."""

    identifier = pet.get("kippyID") or pet.get("kippy_id")
    if identifier is None and include_pet_id:
        identifier = pet.get("petID")
    if identifier is None:
        return None
    try:
        return int(identifier)
    except (TypeError, ValueError):
        return None


def update_pet_data(
    pets: Iterable[Mapping[str, Any]],
    pet_id: int | str,
    current: MutableMapping[str, Any],
    preserve: Sequence[str] | None = None,
) -> MutableMapping[str, Any]:
    """Return the latest pet data from ``pets`` preserving ``preserve`` keys."""

    preserve = tuple(preserve or ())
    for pet in pets:
        if pet.get("petID") != pet_id:
            continue
        if preserve:
            for field in preserve:
                if field in current and field not in pet:
                    pet[field] = current[field]
        return cast(MutableMapping[str, Any], pet)
    return current
