from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kippy import helpers as helpers_module
from custom_components.kippy.const import DOMAIN
from custom_components.kippy.helpers import (
    MAP_REFRESH_IDLE_KEY,
    MAP_REFRESH_LIVE_KEY,
    MapRefreshSettings,
    async_update_map_refresh_settings,
    build_device_info,
    get_map_refresh_settings,
    normalize_kippy_identifier,
    update_pet_data,
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


def test_update_pet_data_preserves_and_returns_current() -> None:
    """update_pet_data preserves requested fields and returns current when missing."""

    pets = [
        {"petID": 1, "value": 1},
        {"petID": 2, "value": 2},
    ]
    current = {"petID": 2, "value": 3, "keep": True}
    updated = update_pet_data(pets, 2, current, preserve=("keep",))
    assert updated["value"] == 2
    assert updated["keep"] is True
    missing = update_pet_data(pets, 3, current)
    assert missing is current


def test_normalize_refresh_value_invalid_inputs() -> None:
    """_normalize_refresh_value handles invalid data."""

    assert helpers_module._normalize_refresh_value("bad") is None
    assert helpers_module._normalize_refresh_value(0) is None


def test_get_map_refresh_settings_invalid_mapping() -> None:
    """Invalid stored structures result in None settings."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={"map_refresh_settings": {"1": "invalid"}},
    )
    assert get_map_refresh_settings(entry, 1) is None

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "map_refresh_settings": {
                "1": {"idle_seconds": "-10", "live_seconds": "bad"}
            }
        },
    )
    assert get_map_refresh_settings(entry, 1) is None


def test_collect_refresh_updates_filters_invalid_values() -> None:
    """Only normalized refresh values are returned in updates."""

    updates = helpers_module._collect_refresh_updates(5, "bad")
    assert updates == {MAP_REFRESH_IDLE_KEY: 5}
    assert MAP_REFRESH_LIVE_KEY not in updates
    assert helpers_module._collect_refresh_updates(None, None) == {}
    assert helpers_module._collect_refresh_updates(None, 8) == {MAP_REFRESH_LIVE_KEY: 8}


def test_collect_refresh_updates_accepts_string_values() -> None:
    """String inputs are normalized for both idle and live refresh updates."""

    updates = helpers_module._collect_refresh_updates("15", "20")
    assert updates == {
        MAP_REFRESH_IDLE_KEY: 15,
        MAP_REFRESH_LIVE_KEY: 20,
    }


@pytest.mark.asyncio
async def test_async_update_map_refresh_settings_no_updates() -> None:
    """Calling update without values exits early."""

    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="3", options={})
    hass = MagicMock()
    hass.config_entries.async_update_entry = AsyncMock()

    await async_update_map_refresh_settings(hass, entry, 4)

    hass.config_entries.async_update_entry.assert_not_awaited()
