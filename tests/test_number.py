# pylint: disable=missing-function-docstring,protected-access,duplicate-code

"""Tests for Kippy number entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.kippy.const import DOMAIN
from custom_components.kippy.number import (
    KippyActivityRefreshDelayNumber,
    KippyIdleUpdateFrequencyNumber,
    KippyLiveUpdateFrequencyNumber,
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
    map_coordinator.config_entry = MagicMock()

    idle = KippyIdleUpdateFrequencyNumber(map_coordinator, pet)
    live = KippyLiveUpdateFrequencyNumber(map_coordinator, pet)
    assert idle.native_value == 5.0
    assert live.native_value == 10.0
    idle.async_write_ha_state = MagicMock()
    live.async_write_ha_state = MagicMock()
    hass = MagicMock()
    idle.hass = hass
    live.hass = hass
    with patch(
        "custom_components.kippy.number.async_update_map_refresh_settings",
        AsyncMock(),
    ) as update_options:
        await idle.async_set_native_value(6)
        await live.async_set_native_value(7)
    map_coordinator.async_set_idle_refresh.assert_called_once_with(360)
    map_coordinator.async_set_live_refresh.assert_called_once_with(7)
    assert update_options.await_count == 2
    idle_call = update_options.await_args_list[0]
    assert idle_call.args == (hass, map_coordinator.config_entry, 1)
    assert idle_call.kwargs == {"idle_seconds": 360}
    live_call = update_options.await_args_list[1]
    assert live_call.args == (hass, map_coordinator.config_entry, 1)
    assert live_call.kwargs == {"live_seconds": 7}
    idle.async_write_ha_state.assert_called_once()
    live.async_write_ha_state.assert_called_once()
    idle_info = idle.device_info
    live_info = live.device_info
    assert (DOMAIN, "1") in idle_info["identifiers"]
    assert (DOMAIN, "1") in live_info["identifiers"]


@pytest.mark.asyncio
async def test_activity_refresh_delay_number() -> None:
    """Activity refresh delay number interacts with timer."""
    pet = {"petID": 1, "petName": "Rex"}
    timer = MagicMock()
    timer.delay_minutes = 2
    timer.async_set_delay = AsyncMock()
    number = KippyActivityRefreshDelayNumber(timer, pet)
    assert number.native_value == 2.0
    number.async_write_ha_state = MagicMock()
    await number.async_set_native_value(5)
    timer.async_set_delay.assert_awaited_once_with(5)
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
    timer = MagicMock()
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "coordinator": base_coordinator,
                "map_coordinators": {1: map_coordinator},
                "activity_timers": {1: timer},
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
            entry.entry_id: {
                "coordinator": base_coordinator,
                "map_coordinators": {},
                "activity_timers": {},
            }
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
        DOMAIN: {
            entry.entry_id: {
                "coordinator": base_coordinator,
                "map_coordinators": {},
                "activity_timers": {},
            }
        }
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
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "coordinator": base_coordinator,
                "map_coordinators": {},
                "activity_timers": {},
            }
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once_with([])


def test_numbers_raise_for_sync_setters() -> None:
    """Synchronous setters on number entities are unsupported."""

    coordinator = MagicMock()
    coordinator.data = {"pets": []}
    coordinator.async_add_listener = MagicMock()
    gps_number = KippyUpdateFrequencyNumber(coordinator, {"petID": 1})
    with pytest.raises(NotImplementedError):
        gps_number.set_native_value(1)

    map_coordinator = MagicMock()
    map_coordinator.async_add_listener = MagicMock()
    idle_number = KippyIdleUpdateFrequencyNumber(map_coordinator, {"petID": 2})
    with pytest.raises(NotImplementedError):
        idle_number.set_native_value(1)

    live_number = KippyLiveUpdateFrequencyNumber(map_coordinator, {"petID": 3})
    with pytest.raises(NotImplementedError):
        live_number.set_native_value(1)

    timer = MagicMock()
    timer.delay_minutes = 0
    activity_number = KippyActivityRefreshDelayNumber(timer, {"petID": 4})
    with pytest.raises(NotImplementedError):
        activity_number.set_native_value(1)
