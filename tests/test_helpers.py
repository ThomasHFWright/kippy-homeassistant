from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kippy.const import DOMAIN
from custom_components.kippy.helpers import (
    MapRefreshSettings,
    async_update_map_refresh_settings,
    build_device_info,
    get_map_refresh_settings,
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


def test_get_map_refresh_settings_missing() -> None:
    """None is returned when there are no stored map refresh options."""

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    assert get_map_refresh_settings(entry, 1) is None


def test_get_map_refresh_settings_parses_values() -> None:
    """Stored map refresh settings are converted to integers."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "map_refresh_settings": {"1": {"idle_seconds": "480", "live_seconds": 15}}
        },
    )
    settings = get_map_refresh_settings(entry, 1)
    assert isinstance(settings, MapRefreshSettings)
    assert settings.idle_seconds == 480
    assert settings.live_seconds == 15


@pytest.mark.asyncio
async def test_async_update_map_refresh_settings_updates_entry() -> None:
    """Persisting map refresh settings updates the config entry options."""

    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="1", options={})
    hass = MagicMock()
    hass.config_entries.async_update_entry = AsyncMock()

    await async_update_map_refresh_settings(hass, entry, 2, idle_seconds=600)

    hass.config_entries.async_update_entry.assert_awaited_once()
    call = hass.config_entries.async_update_entry.await_args
    assert call.args == (entry,)
    options = call.kwargs["options"]
    assert options["map_refresh_settings"]["2"]["idle_seconds"] == 600

    # Subsequent calls with unchanged values should avoid extra updates.
    hass.config_entries.async_update_entry.reset_mock()
    entry_with_options = MockConfigEntry(
        domain=DOMAIN, data={}, entry_id="2", options=options
    )
    await async_update_map_refresh_settings(
        hass, entry_with_options, 2, idle_seconds=600
    )
    hass.config_entries.async_update_entry.assert_not_awaited()
