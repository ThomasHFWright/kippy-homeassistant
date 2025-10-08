"""Helper utilities for the Kippy integration."""

from __future__ import annotations

from asyncio import TimeoutError as AsyncioTimeoutError
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from inspect import isawaitable
from json import JSONDecodeError
from typing import Any, cast

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DEFAULT_DEVICE_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_DEVICE_UPDATE_INTERVAL_MINUTES,
    MIN_DEVICE_UPDATE_INTERVAL_MINUTES,
)

API_EXCEPTIONS: tuple[type[Exception], ...] = (
    ClientError,
    AsyncioTimeoutError,
    RuntimeError,
    JSONDecodeError,
)

MAP_REFRESH_OPTIONS_KEY = "map_refresh_settings"
MAP_REFRESH_IDLE_KEY = "idle_seconds"
MAP_REFRESH_LIVE_KEY = "live_seconds"

DEVICE_UPDATE_INTERVAL_KEY = "device_update_interval"


@dataclass(slots=True)
class MapRefreshSettings:
    """Persisted refresh configuration for a pet's map coordinator."""

    idle_seconds: int = 300
    live_seconds: int = 10


def coerce_int(value: Any) -> int | None:
    """Return ``value`` as an int when possible."""

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_device_update_interval(value: Any) -> int | None:
    """Return a sanitized minutes value for the device update interval."""

    minutes = coerce_int(value)
    if minutes is None:
        return None
    if not (
        MIN_DEVICE_UPDATE_INTERVAL_MINUTES
        <= minutes
        <= MAX_DEVICE_UPDATE_INTERVAL_MINUTES
    ):
        return None
    return minutes


def get_device_update_interval(entry: ConfigEntry) -> int:
    """Return the configured minutes between device updates."""

    normalized = normalize_device_update_interval(
        entry.options.get(DEVICE_UPDATE_INTERVAL_KEY)
    )
    if normalized is not None:
        return normalized
    return DEFAULT_DEVICE_UPDATE_INTERVAL_MINUTES


async def async_update_device_update_interval(
    hass: HomeAssistant, entry: ConfigEntry, minutes: int
) -> None:
    """Persist the config entry option for the device update interval."""

    if entry.options.get(DEVICE_UPDATE_INTERVAL_KEY) == minutes:
        return

    new_options = dict(entry.options)
    new_options[DEVICE_UPDATE_INTERVAL_KEY] = minutes

    update_result = hass.config_entries.async_update_entry(entry, options=new_options)
    if isawaitable(update_result):
        await update_result


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


def _normalize_refresh_value(value: Any) -> int | None:
    """Return ``value`` as a positive integer seconds value when valid."""

    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    if result <= 0:
        return None
    return result


def get_map_refresh_settings(
    entry: ConfigEntry, pet_id: int | str
) -> MapRefreshSettings | None:
    """Return stored map refresh settings for ``pet_id`` if available."""

    options = entry.options.get(MAP_REFRESH_OPTIONS_KEY)
    if not isinstance(options, Mapping):
        return None
    pet_options = options.get(str(pet_id))
    if not isinstance(pet_options, Mapping):
        return None

    idle_seconds = _normalize_refresh_value(pet_options.get(MAP_REFRESH_IDLE_KEY))
    live_seconds = _normalize_refresh_value(pet_options.get(MAP_REFRESH_LIVE_KEY))

    if idle_seconds is None and live_seconds is None:
        return None

    settings = MapRefreshSettings()
    if idle_seconds is not None:
        settings.idle_seconds = idle_seconds
    if live_seconds is not None:
        settings.live_seconds = live_seconds
    return settings


def _collect_refresh_updates(
    idle_seconds: int | None, live_seconds: int | None
) -> dict[str, int]:
    """Return a mapping of updated idle/live refresh values in seconds."""

    updates: dict[str, int] = {}
    if idle_seconds is not None:
        normalized_idle = _normalize_refresh_value(idle_seconds)
        if normalized_idle is not None:
            updates[MAP_REFRESH_IDLE_KEY] = normalized_idle
    if live_seconds is not None:
        normalized_live = _normalize_refresh_value(live_seconds)
        if normalized_live is not None:
            updates[MAP_REFRESH_LIVE_KEY] = normalized_live
    return updates


def _copy_map_refresh_options(entry: ConfigEntry) -> dict[str, dict[str, Any]]:
    """Return a mutable copy of stored map refresh settings."""

    copied: dict[str, dict[str, Any]] = {}
    existing = entry.options.get(MAP_REFRESH_OPTIONS_KEY)
    if not isinstance(existing, Mapping):
        return copied
    for key, value in existing.items():
        if isinstance(key, str) and isinstance(value, Mapping):
            copied[key] = dict(value)
    return copied


async def async_update_map_refresh_settings(
    hass: HomeAssistant,
    entry: ConfigEntry,
    pet_id: int | str,
    *,
    idle_seconds: int | None = None,
    live_seconds: int | None = None,
) -> None:
    """Persist updated map refresh settings for ``pet_id``."""

    updates = _collect_refresh_updates(idle_seconds, live_seconds)
    if not updates:
        return

    pet_key = str(pet_id)
    map_options = _copy_map_refresh_options(entry)
    pet_options = map_options.get(pet_key, {}).copy()

    changed = False
    for option_key, option_value in updates.items():
        if pet_options.get(option_key) != option_value:
            pet_options[option_key] = option_value
            changed = True

    if not changed:
        return

    map_options[pet_key] = pet_options
    new_options = dict(entry.options)
    new_options[MAP_REFRESH_OPTIONS_KEY] = map_options

    update_result = hass.config_entries.async_update_entry(entry, options=new_options)
    if isawaitable(update_result):
        await update_result
