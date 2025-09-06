from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.kippy.const import DOMAIN, OPERATING_STATUS, OPERATING_STATUS_MAP
from custom_components.kippy.switch import (
    KippyEnergySavingSwitch,
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
async def test_live_tracking_switch_turns_on_off() -> None:
    """Live tracking switch calls API and processes data."""
    pet = {"petID": 1, "petName": "Rex"}
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.kippy_id = 1
    coordinator.api.kippymap_action = AsyncMock(
        return_value={"operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]}
    )
    coordinator.process_new_data = MagicMock()
    coordinator.async_add_listener = MagicMock()
    switch = KippyLiveTrackingSwitch(coordinator, pet)
    switch.hass = MagicMock()
    switch.entity_id = "switch.live"
    await switch.async_turn_on()
    coordinator.api.kippymap_action.assert_called()
    coordinator.process_new_data.assert_called()
    coordinator.api.kippymap_action.reset_mock()
    coordinator.process_new_data.reset_mock()
    coordinator.api.kippymap_action.return_value = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    }
    await switch.async_turn_off()
    coordinator.api.kippymap_action.assert_called()
    coordinator.process_new_data.assert_called()


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
    assert not switch.is_on
    await switch.async_turn_on()
    assert map_coord.ignore_lbs is True
    await switch.async_turn_off()
    assert map_coord.ignore_lbs is False


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
