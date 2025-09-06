from unittest.mock import MagicMock

import pytest

from custom_components.kippy.const import (
    DOMAIN,
    LABEL_EXPIRED,
    OPERATING_STATUS,
    OPERATING_STATUS_MAP,
    PET_KIND_TO_TYPE,
)
from custom_components.kippy.sensor import (
    KippyExpiredDaysSensor,
    KippyOperatingStatusSensor,
    KippyPetTypeSensor,
    async_setup_entry,
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

    assert sensor.native_value == OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]


@pytest.mark.asyncio
async def test_sensor_async_setup_entry_creates_entities() -> None:
    """async_setup_entry adds sensors for each pet."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    coordinator = MagicMock()
    coordinator.data = {"pets": [{"petID": 1}]}
    map_coordinator = MagicMock()
    activity_coord = MagicMock()
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "coordinator": coordinator,
                "map_coordinators": {1: map_coordinator},
                "activity_coordinator": activity_coord,
            }
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert any(isinstance(e, KippyExpiredDaysSensor) for e in entities)


@pytest.mark.asyncio
async def test_sensor_async_setup_entry_no_pets() -> None:
    """No sensors added when there are no pets."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    coordinator = MagicMock()
    coordinator.data = {"pets": []}
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "coordinator": coordinator,
                "map_coordinators": {},
                "activity_coordinator": MagicMock(),
            }
        }
    }
    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once_with([])
