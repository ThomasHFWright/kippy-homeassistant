from unittest.mock import MagicMock

import pytest

from custom_components.kippy.binary_sensor import (
    KippyFirmwareUpgradeAvailableBinarySensor,
    async_setup_entry,
)
from custom_components.kippy.const import DOMAIN


@pytest.mark.asyncio
async def test_firmware_sensor_updates_state() -> None:
    """Firmware sensor reflects upgrade availability and updates with coordinator."""
    pet = {"petID": 1, "petName": "Rex", "firmware_need_upgrade": True}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyFirmwareUpgradeAvailableBinarySensor(coordinator, pet)

    assert sensor.is_on is True

    updated = {"petID": 1, "petName": "Rex", "firmware_need_upgrade": False}
    coordinator.data = {"pets": [updated]}
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    assert sensor.is_on is False


@pytest.mark.asyncio
async def test_firmware_sensor_device_info() -> None:
    """Device info uses helper data."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyFirmwareUpgradeAvailableBinarySensor(coordinator, pet)
    info = sensor.device_info
    assert info["identifiers"]


@pytest.mark.asyncio
async def test_binary_sensor_async_setup_entry_creates_entities() -> None:
    """async_setup_entry adds firmware upgrade sensors for each pet."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    coordinator = MagicMock()
    coordinator.data = {"pets": [{"petID": 1}]}
    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], KippyFirmwareUpgradeAvailableBinarySensor)


@pytest.mark.asyncio
async def test_binary_sensor_async_setup_entry_no_pets() -> None:
    """No entities are added when no pets are configured."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    coordinator = MagicMock()
    coordinator.data = {"pets": []}
    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once_with([])
