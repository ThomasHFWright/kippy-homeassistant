from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.kippy.const import DOMAIN
from custom_components.kippy.number import (
    KippyIdleUpdateFrequencyNumber,
    KippyLiveUpdateFrequencyNumber,
    KippyActivityRefreshDelayNumber,
    KippyUpdateFrequencyNumber,
    async_setup_entry,
)


@pytest.mark.asyncio
async def test_update_frequency_number() -> None:
    """Ensure native value and setting value update pet data."""
    pet = {
        "petID": 1,
        "petName": "Rex",
        "updateFrequency": 5,
        "kippyID": 2,
        "gpsOnDefault": 1,
    }
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    coordinator.api.modify_kippy_settings = AsyncMock(
        return_value={"update_frequency": 10}
    )
    number = KippyUpdateFrequencyNumber(coordinator, pet)
    assert number.native_value == 5.0
    number.async_write_ha_state = MagicMock()
    await number.async_set_native_value(10)
    coordinator.api.modify_kippy_settings.assert_awaited_once_with(
        2, update_frequency=10.0, gps_on_default=True
    )
    assert pet["updateFrequency"] == 10
    number.async_write_ha_state.assert_called_once()
    coordinator.data = {"pets": [{"petID": 1, "updateFrequency": 20}]}
    number.async_write_ha_state.reset_mock()
    number._handle_coordinator_update()
    assert number.native_value == 20.0
    number.async_write_ha_state.assert_called_once()
    info = number.device_info
    assert (DOMAIN, "1") in info["identifiers"]


@pytest.mark.asyncio
async def test_update_frequency_number_missing() -> None:
    """Missing updateFrequency returns None."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    number = KippyUpdateFrequencyNumber(coordinator, pet)
    assert number.native_value is None
    info = number.device_info
    assert (DOMAIN, "1") in info["identifiers"]


@pytest.mark.asyncio
async def test_update_frequency_number_api_error() -> None:
    """API errors are propagated and state not updated."""

    pet = {"petID": 1, "petName": "Rex", "updateFrequency": 5, "kippyID": 2}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    coordinator.api.modify_kippy_settings = AsyncMock(side_effect=RuntimeError)
    number = KippyUpdateFrequencyNumber(coordinator, pet)
    number.async_write_ha_state = MagicMock()
    with pytest.raises(RuntimeError):
        await number.async_set_native_value(10)
    assert pet["updateFrequency"] == 5
    number.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_update_frequency_number_sends_current_gps() -> None:
    """Both True and False GPS defaults are forwarded when updating."""

    pet = {
        "petID": 1,
        "petName": "Rex",
        "updateFrequency": 5,
        "kippyID": 2,
        "gpsOnDefault": 0,
    }
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    coordinator.api.modify_kippy_settings = AsyncMock(
        return_value={"update_frequency": 6}
    )
    number = KippyUpdateFrequencyNumber(coordinator, pet)
    number.async_write_ha_state = MagicMock()
    await number.async_set_native_value(6)
    coordinator.api.modify_kippy_settings.assert_awaited_once_with(
        2, update_frequency=6.0, gps_on_default=False
    )
    assert pet["updateFrequency"] == 6
    number.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_update_frequency_number_no_kippy_id() -> None:
    """Setting value when kippy ID missing updates local data only."""

    pet = {"petID": 1, "petName": "Rex", "updateFrequency": 5}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    coordinator.api.modify_kippy_settings = AsyncMock()
    number = KippyUpdateFrequencyNumber(coordinator, pet)
    number.async_write_ha_state = MagicMock()
    await number.async_set_native_value(8)
    assert pet["updateFrequency"] == 8
    coordinator.api.modify_kippy_settings.assert_not_called()
    number.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_idle_and_live_numbers() -> None:
    """Idle and live numbers interact with coordinator."""
    pet = {"petID": 1, "petName": "Rex"}
    map_coordinator = MagicMock()
    map_coordinator.idle_refresh = 300
    map_coordinator.live_refresh = 10
    map_coordinator.async_set_idle_refresh = AsyncMock()
    map_coordinator.async_set_live_refresh = AsyncMock()
    map_coordinator.async_add_listener = MagicMock()

    idle = KippyIdleUpdateFrequencyNumber(map_coordinator, pet)
    live = KippyLiveUpdateFrequencyNumber(map_coordinator, pet)
    assert idle.native_value == 5.0
    assert live.native_value == 10.0
    idle.async_write_ha_state = MagicMock()
    live.async_write_ha_state = MagicMock()
    await idle.async_set_native_value(6)
    await live.async_set_native_value(7)
    map_coordinator.async_set_idle_refresh.assert_called_once_with(360)
    map_coordinator.async_set_live_refresh.assert_called_once_with(7)
    idle.async_write_ha_state.assert_called_once()
    live.async_write_ha_state.assert_called_once()
    idle_info = idle.device_info
    live_info = live.device_info
    assert (DOMAIN, "1") in idle_info["identifiers"]
    assert (DOMAIN, "1") in live_info["identifiers"]


@pytest.mark.asyncio
async def test_activity_refresh_delay_number() -> None:
    """Activity refresh delay number interacts with coordinator."""
    pet = {"petID": 1, "petName": "Rex"}
    map_coordinator = MagicMock()
    map_coordinator.activity_refresh_delay = 120
    map_coordinator.async_set_activity_refresh_delay = AsyncMock()
    map_coordinator.async_add_listener = MagicMock()

    number = KippyActivityRefreshDelayNumber(map_coordinator, pet)
    assert number.native_value == 2.0
    number.async_write_ha_state = MagicMock()
    await number.async_set_native_value(3)
    map_coordinator.async_set_activity_refresh_delay.assert_awaited_once_with(180)
    number.async_write_ha_state.assert_called_once()
    info = number.device_info
    assert (DOMAIN, "1") in info["identifiers"]


@pytest.mark.asyncio
async def test_number_async_setup_entry_creates_entities() -> None:
    """async_setup_entry adds number entities for each pet."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    base_coordinator = MagicMock()
    base_coordinator.data = {"pets": [{"petID": 1}]}
    map_coordinator = MagicMock()
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "coordinator": base_coordinator,
                "map_coordinators": {1: map_coordinator},
            }
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert any(isinstance(e, KippyUpdateFrequencyNumber) for e in entities)
    assert any(isinstance(e, KippyIdleUpdateFrequencyNumber) for e in entities)
    assert any(isinstance(e, KippyLiveUpdateFrequencyNumber) for e in entities)
    assert any(isinstance(e, KippyActivityRefreshDelayNumber) for e in entities)


@pytest.mark.asyncio
async def test_number_async_setup_entry_no_pets() -> None:
    """No number entities added when there are no pets."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    base_coordinator = MagicMock()
    base_coordinator.data = {"pets": []}
    hass.data = {
        DOMAIN: {
            entry.entry_id: {"coordinator": base_coordinator, "map_coordinators": {}}
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once_with([])


@pytest.mark.asyncio
async def test_number_async_setup_entry_missing_map() -> None:
    """Only base numbers added when map coordinator is missing."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    base_coordinator = MagicMock()
    base_coordinator.data = {"pets": [{"petID": 1}]}
    hass.data = {
        DOMAIN: {entry.entry_id: {"coordinator": base_coordinator, "map_coordinators": {}}}
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert all(isinstance(e, KippyUpdateFrequencyNumber) for e in entities)


@pytest.mark.asyncio
async def test_number_async_setup_entry_expired_pet() -> None:
    """Expired pets should not create number entities."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    base_coordinator = MagicMock()
    base_coordinator.data = {"pets": [{"petID": 1, "expired_days": 0}]}
    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": base_coordinator, "map_coordinators": {}}}}
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once_with([])
