from unittest.mock import MagicMock

import pytest

from custom_components.kippy.const import LABEL_EXPIRED, PET_KIND_TO_TYPE
from custom_components.kippy.const import OPERATING_STATUS, OPERATING_STATUS_MAP
from custom_components.kippy.sensor import (
    KippyExpiredDaysSensor,
    KippyOperatingStatusSensor,
    KippyPetTypeSensor,
)


@pytest.mark.asyncio
async def test_expired_days_sensor_returns_expired() -> None:
    """Ensure non-negative days report as 'Expired'."""
    pet = {"petID": "1", "expired_days": 0}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyExpiredDaysSensor(coordinator, pet)

    assert sensor.native_value == LABEL_EXPIRED

    pet["expired_days"] = 5
    assert sensor.native_value == LABEL_EXPIRED


@pytest.mark.asyncio
async def test_expired_days_sensor_returns_positive_days() -> None:
    """Negative days are returned as positive remaining days."""
    pet = {"petID": "1", "expired_days": -3}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyExpiredDaysSensor(coordinator, pet)

    assert sensor.native_value == 3


@pytest.mark.asyncio
async def test_pet_type_sensor_maps_kind_to_type() -> None:
    """Pet type sensor should map kind code to type label."""
    pet = {"petID": "1", "petKind": "4"}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyPetTypeSensor(coordinator, pet)

    assert sensor.native_value == PET_KIND_TO_TYPE["4"]


@pytest.mark.asyncio
async def test_operating_status_sensor_returns_string() -> None:
    """Operating status sensor should expose a human readable value."""
    pet = {"petID": "1"}
    coordinator = MagicMock()
    coordinator.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    }
    coordinator.async_add_listener = MagicMock()
    sensor = KippyOperatingStatusSensor(coordinator, pet)

    assert (
        sensor.native_value
        == OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    )
