from unittest.mock import MagicMock

import pytest

from custom_components.kippy.binary_sensor import (
    KippyFirmwareUpgradeAvailableBinarySensor,
)


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
