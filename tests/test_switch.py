# pylint: disable=missing-function-docstring,protected-access,duplicate-code

"""Tests for Kippy switch entities."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.kippy.const import (
    APP_ACTION,
    DOMAIN,
    OPERATING_STATUS,
    OPERATING_STATUS_MAP,
)
from custom_components.kippy.switch import (
    KippyEnergySavingSwitch,
    KippyGpsDefaultSwitch,
    KippyIgnoreLBSSwitch,
    KippyLiveTrackingSwitch,
    async_setup_entry,
)


@pytest.mark.asyncio
async def test_energy_saving_switch_updates_from_operating_status() -> None:
    """Energy saving switch turns on when operating status is energy saving."""
    pet = {"petID": "1", "energySavingMode": 0}

    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    map_coordinator = MagicMock()
    map_coordinator.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    }
    map_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    switch = KippyEnergySavingSwitch(coordinator, pet, map_coordinator)
    switch.async_write_ha_state = MagicMock()

    assert not switch.is_on

    switch._handle_map_update()

    assert switch.is_on
    assert pet["energySavingMode"] == 1


@pytest.mark.asyncio
async def test_energy_saving_switch_preserves_pending_off() -> None:
    """Energy saving switch keeps pending off when still energy saving."""
    pet = {"petID": "1", "energySavingMode": 1}

    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.async_set_updated_data = MagicMock()

    map_coordinator = MagicMock()
    map_coordinator.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    }
    map_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    switch = KippyEnergySavingSwitch(coordinator, pet, map_coordinator)
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_off()
    assert pet["energySavingMode"] == 0
    assert pet["energySavingModePending"]
    coordinator.async_set_updated_data.reset_mock()

    switch._handle_map_update()
    assert pet["energySavingMode"] == 0
    assert pet["energySavingModePending"]
    coordinator.async_set_updated_data.assert_not_called()


def test_live_tracking_switch_operating_status() -> None:
    """Live tracking switch follows operating status and availability."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.STARTING_LIVE]
    }
    coordinator.async_add_listener = MagicMock()
    coordinator.last_update_success = True
    switch = KippyLiveTrackingSwitch(coordinator, pet)
    switch.hass = MagicMock()
    switch.entity_id = "switch.live"
    switch.async_write_ha_state = MagicMock()

    assert switch.is_on
    assert switch.available

    coordinator.data["operating_status"] = OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]
    switch._handle_coordinator_update()
    assert switch.is_on

    coordinator.data["operating_status"] = OPERATING_STATUS_MAP[OPERATING_STATUS.IDLE]
    switch._handle_coordinator_update()
    assert not switch.is_on
    assert switch.available

    coordinator.data["operating_status"] = OPERATING_STATUS_MAP[
        OPERATING_STATUS.ENERGY_SAVING
    ]
    switch._handle_coordinator_update()
    assert not switch.is_on
    assert not switch.available


@pytest.mark.asyncio
async def test_live_tracking_switch_unavailable_energy_saving() -> None:
    """Live tracking switch is unavailable and blocks toggling in energy saving mode."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    }
    coordinator.async_add_listener = MagicMock()
    coordinator.api.kippymap_action = AsyncMock()
    coordinator.kippy_id = 1
    switch = KippyLiveTrackingSwitch(coordinator, pet)
    switch.hass = MagicMock()
    switch.entity_id = "switch.live"
    switch.async_write_ha_state = MagicMock()

    assert not switch.is_on
    assert not switch.available

    with pytest.raises(HomeAssistantError):
        await switch.async_turn_on()
    assert switch.async_write_ha_state.called
    assert not switch.is_on

    switch.async_write_ha_state.reset_mock()

    with pytest.raises(HomeAssistantError):
        await switch.async_turn_off()
    assert switch.async_write_ha_state.called
    assert not switch.is_on
    coordinator.api.kippymap_action.assert_not_called()


@pytest.mark.asyncio
async def test_energy_saving_switch_calls_api() -> None:
    """Energy saving switch sends API requests when toggled."""
    pet = {"petID": "1", "energySavingMode": 0, "kippyID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.api.modify_kippy_settings = AsyncMock()
    map_coordinator = MagicMock()
    map_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    switch = KippyEnergySavingSwitch(coordinator, pet, map_coordinator)
    switch.async_write_ha_state = MagicMock()
    await switch.async_turn_on()
    await switch.async_turn_off()
    coordinator.api.modify_kippy_settings.assert_has_awaits(
        [
            call(1, energy_saving_mode=True),
            call(1, energy_saving_mode=False),
        ]
    )


@pytest.mark.asyncio
async def test_live_tracking_switch_turns_on_off() -> None:
    """Live tracking switch calls API and processes data."""
    pet = {"petID": 1, "petName": "Rex"}
    coordinator = MagicMock()
    coordinator.data = {"operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.IDLE]}
    coordinator.kippy_id = 1
    coordinator.api.kippymap_action = AsyncMock(
        return_value={"operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]}
    )

    def _process_new_data(data: dict) -> None:
        coordinator.data.update(data)

    coordinator.process_new_data = MagicMock(side_effect=_process_new_data)
    coordinator.async_add_listener = MagicMock()
    switch = KippyLiveTrackingSwitch(coordinator, pet)
    switch.hass = MagicMock()
    switch.entity_id = "switch.live"
    switch.async_write_ha_state = MagicMock()
    await switch.async_turn_on()
    coordinator.api.kippymap_action.assert_called_once_with(
        1, app_action=APP_ACTION.TURN_LIVE_TRACKING_ON
    )
    coordinator.process_new_data.assert_called_once()
    assert (
        coordinator.data.get("operating_status")
        == OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]
    )
    coordinator.api.kippymap_action.reset_mock()
    coordinator.process_new_data.reset_mock()
    coordinator.api.kippymap_action.return_value = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]
    }
    coordinator.data["operating_status"] = OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]
    await switch.async_turn_off()
    coordinator.api.kippymap_action.assert_called_once_with(
        1, app_action=APP_ACTION.TURN_LIVE_TRACKING_OFF
    )
    coordinator.process_new_data.assert_called_once()
    assert (
        coordinator.data.get("operating_status")
        == OPERATING_STATUS_MAP[OPERATING_STATUS.IDLE]
    )


@pytest.mark.asyncio
async def test_live_tracking_switch_turn_on_sets_starting_live() -> None:
    """Live tracking switch falls back to starting live when API returns idle."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {"operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.IDLE]}
    coordinator.kippy_id = 1
    coordinator.api.kippymap_action = AsyncMock(
        return_value={"operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.IDLE]}
    )
    coordinator.process_new_data = MagicMock()
    coordinator.async_add_listener = MagicMock()
    switch = KippyLiveTrackingSwitch(coordinator, pet)
    switch.hass = MagicMock()
    switch.entity_id = "switch.live"
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_on()

    coordinator.api.kippymap_action.assert_called_once_with(
        1, app_action=APP_ACTION.TURN_LIVE_TRACKING_ON
    )
    coordinator.process_new_data.assert_called_once()
    assert (
        coordinator.data.get("operating_status")
        == OPERATING_STATUS_MAP[OPERATING_STATUS.STARTING_LIVE]
    )


@pytest.mark.asyncio
async def test_live_tracking_switch_turn_off_from_starting_live() -> None:
    """Turning off live tracking clears starting live status."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.STARTING_LIVE]
    }
    coordinator.kippy_id = 1
    coordinator.api.kippymap_action = AsyncMock(
        return_value={
            "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.STARTING_LIVE]
        }
    )
    coordinator.process_new_data = MagicMock()
    coordinator.async_add_listener = MagicMock()
    switch = KippyLiveTrackingSwitch(coordinator, pet)
    switch.hass = MagicMock()
    switch.entity_id = "switch.live"
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_off()

    coordinator.api.kippymap_action.assert_called_once_with(
        1, app_action=APP_ACTION.TURN_LIVE_TRACKING_OFF
    )
    coordinator.process_new_data.assert_called_once()
    assert (
        coordinator.data.get("operating_status")
        == OPERATING_STATUS_MAP[OPERATING_STATUS.IDLE]
    )


@pytest.mark.asyncio
async def test_live_tracking_switch_propagates_error() -> None:
    """Errors from API propagate out of the switch."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.kippy_id = 1
    coordinator.api.kippymap_action = AsyncMock(side_effect=RuntimeError)
    coordinator.async_add_listener = MagicMock()
    switch = KippyLiveTrackingSwitch(coordinator, pet)
    switch.hass = MagicMock()
    switch.entity_id = "switch.live"
    switch.async_write_ha_state = MagicMock()
    with pytest.raises(RuntimeError):
        await switch.async_turn_on()


@pytest.mark.asyncio
async def test_ignore_lbs_switch_toggles_coordinator() -> None:
    """Ignore LBS switch mirrors coordinator flag."""
    pet = {"petID": 1, "petName": "Rex"}
    map_coord = MagicMock()
    map_coord.ignore_lbs = False
    map_coord.async_add_listener = MagicMock()
    switch = KippyIgnoreLBSSwitch(map_coord, pet)
    switch.hass = MagicMock()
    switch.entity_id = "switch.lbs"
    switch.async_write_ha_state = MagicMock()
    assert not switch.is_on
    await switch.async_turn_on()
    assert map_coord.ignore_lbs is True
    await switch.async_turn_off()
    assert map_coord.ignore_lbs is False


@pytest.mark.asyncio
async def test_gps_switch_calls_api() -> None:
    """GPS activation switch toggles via API."""
    pet = {"petID": 1, "petName": "Rex", "gpsOnDefault": 1, "kippyID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.api.modify_kippy_settings = AsyncMock()
    switch = KippyGpsDefaultSwitch(coordinator, pet)
    switch.async_write_ha_state = MagicMock()
    assert switch.is_on
    await switch.async_turn_off()
    await switch.async_turn_on()
    coordinator.api.modify_kippy_settings.assert_has_awaits(
        [
            call(1, gps_on_default=False),
            call(1, gps_on_default=True),
        ]
    )


@pytest.mark.asyncio
async def test_energy_saving_switch_api_error() -> None:
    """Errors from API propagate for energy saving switch."""

    pet = {"petID": "1", "energySavingMode": 0, "kippyID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.api.modify_kippy_settings = AsyncMock(side_effect=RuntimeError)
    map_coordinator = MagicMock()
    map_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    switch = KippyEnergySavingSwitch(coordinator, pet, map_coordinator)
    switch.async_write_ha_state = MagicMock()
    with pytest.raises(RuntimeError):
        await switch.async_turn_on()
    assert pet["energySavingMode"] == 0
    switch.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_gps_switch_api_error() -> None:
    """Errors from API propagate for GPS activation switch."""

    pet = {"petID": 1, "gpsOnDefault": 1, "kippyID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.api.modify_kippy_settings = AsyncMock(side_effect=RuntimeError)
    switch = KippyGpsDefaultSwitch(coordinator, pet)
    switch.async_write_ha_state = MagicMock()
    with pytest.raises(RuntimeError):
        await switch.async_turn_off()
    assert pet["gpsOnDefault"] == 1
    switch.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_energy_saving_switch_no_kippy_id() -> None:
    """Switch updates local state without API when kippy ID missing."""

    pet = {"petID": "1", "energySavingMode": 0}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.api.modify_kippy_settings = AsyncMock()
    map_coordinator = MagicMock()
    map_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    switch = KippyEnergySavingSwitch(coordinator, pet, map_coordinator)
    switch.async_write_ha_state = MagicMock()
    await switch.async_turn_on()
    assert pet["energySavingMode"] == 1
    coordinator.api.modify_kippy_settings.assert_not_called()
    switch.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_gps_switch_no_kippy_id() -> None:
    """GPS activation switch toggles without API when kippy ID missing."""

    pet = {"petID": 1, "gpsOnDefault": 0}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.api.modify_kippy_settings = AsyncMock()
    switch = KippyGpsDefaultSwitch(coordinator, pet)
    switch.async_write_ha_state = MagicMock()
    await switch.async_turn_on()
    assert pet["gpsOnDefault"] == 1
    coordinator.api.modify_kippy_settings.assert_not_called()
    switch.async_write_ha_state.assert_called_once()


def test_gps_switch_handle_coordinator_update() -> None:
    """_handle_coordinator_update refreshes pet data."""

    pet = {"petID": 1, "gpsOnDefault": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [{"petID": 1, "gpsOnDefault": 0}]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    switch = KippyGpsDefaultSwitch(coordinator, pet)
    switch.async_write_ha_state = MagicMock()
    switch._handle_coordinator_update()
    assert not switch.is_on
    switch.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_switch_async_setup_entry_creates_entities() -> None:
    """async_setup_entry adds all switch entities for each pet."""
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
    assert any(isinstance(e, KippyEnergySavingSwitch) for e in entities)
    assert any(isinstance(e, KippyLiveTrackingSwitch) for e in entities)
    assert any(isinstance(e, KippyIgnoreLBSSwitch) for e in entities)
    assert any(isinstance(e, KippyGpsDefaultSwitch) for e in entities)


@pytest.mark.asyncio
async def test_switch_async_setup_entry_no_pets() -> None:
    """No switches added when there are no pets."""
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
async def test_switch_async_setup_entry_expired_pet() -> None:
    """Expired pets should not create switch entities."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    base_coordinator = MagicMock()
    base_coordinator.data = {"pets": [{"petID": 1, "expired_days": 0}]}
    hass.data = {
        DOMAIN: {
            entry.entry_id: {"coordinator": base_coordinator, "map_coordinators": {}}
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once_with([])


@pytest.mark.asyncio
async def test_switch_async_setup_entry_missing_map() -> None:
    """No switches added when map coordinator is missing."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    base_coordinator = MagicMock()
    base_coordinator.data = {"pets": [{"petID": 1}]}
    hass.data = {
        DOMAIN: {
            entry.entry_id: {"coordinator": base_coordinator, "map_coordinators": {}}
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], KippyGpsDefaultSwitch)


def test_energy_saving_switch_turn_on_off_and_device_info() -> None:
    """Energy saving switch toggles pet data and exposes device info."""
    pet = {"petID": "1", "petName": "Rex", "energySavingMode": 0, "kippyID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.api.modify_kippy_settings = AsyncMock()
    map_coord = MagicMock()
    map_coord.async_add_listener = MagicMock(return_value=MagicMock())
    map_coord.data = {}
    switch = KippyEnergySavingSwitch(coordinator, pet, map_coord)
    switch.async_write_ha_state = MagicMock()
    assert not switch.is_on
    loop = asyncio.get_event_loop()
    loop.run_until_complete(switch.async_turn_on())
    assert switch.is_on
    loop.run_until_complete(switch.async_turn_off())
    assert not switch.is_on
    coordinator.data = {
        "pets": [{"petID": "1", "petName": "Rex", "energySavingMode": 1}]
    }
    switch._handle_coordinator_update()
    assert switch.is_on
    assert switch.device_info["name"] == "Kippy Rex"


def test_live_and_ignore_lbs_device_info() -> None:
    """Other switches expose device info correctly."""
    pet = {"petID": 1, "petName": "Rex"}
    map_coord = MagicMock()
    map_coord.data = {}
    map_coord.async_add_listener = MagicMock()
    live = KippyLiveTrackingSwitch(map_coord, pet)
    ignore = KippyIgnoreLBSSwitch(map_coord, pet)
    assert live.device_info["name"] == "Kippy Rex"
    assert ignore.device_info["name"] == "Kippy Rex"


def test_energy_saving_switch_handle_map_update_no_data() -> None:
    """Map updates without data are ignored."""

    pet = {"petID": 1, "energySavingMode": 0}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.async_set_updated_data = MagicMock()
    map_coord = MagicMock()
    map_coord.data = {}
    map_coord.async_add_listener = MagicMock(return_value=MagicMock())
    switch = KippyEnergySavingSwitch(coordinator, pet, map_coord)
    switch.async_write_ha_state = MagicMock()

    switch._handle_map_update()

    switch.async_write_ha_state.assert_not_called()
    coordinator.async_set_updated_data.assert_not_called()


def test_switches_raise_for_sync_methods() -> None:
    """Synchronous switch methods are not supported."""

    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    gps = KippyGpsDefaultSwitch(coordinator, pet.copy())
    with pytest.raises(NotImplementedError):
        gps.turn_on()
    with pytest.raises(NotImplementedError):
        gps.turn_off()

    map_coord = MagicMock()
    map_coord.async_add_listener = MagicMock(return_value=MagicMock())
    energy = KippyEnergySavingSwitch(coordinator, pet.copy(), map_coord)
    with pytest.raises(NotImplementedError):
        energy.turn_on()
    with pytest.raises(NotImplementedError):
        energy.turn_off()

    map_coord2 = MagicMock()
    map_coord2.data = {}
    map_coord2.async_add_listener = MagicMock(return_value=MagicMock())
    live = KippyLiveTrackingSwitch(map_coord2, pet.copy())
    with pytest.raises(NotImplementedError):
        live.turn_on()
    with pytest.raises(NotImplementedError):
        live.turn_off()

    ignore = KippyIgnoreLBSSwitch(map_coord2, pet.copy())
    with pytest.raises(NotImplementedError):
        ignore.turn_on()
    with pytest.raises(NotImplementedError):
        ignore.turn_off()
