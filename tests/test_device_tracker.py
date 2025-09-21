from unittest.mock import MagicMock

import pytest

from custom_components.kippy.const import DOMAIN, PET_KIND_TO_TYPE
from custom_components.kippy.device_tracker import KippyPetTracker, async_setup_entry


@pytest.mark.asyncio
async def test_tracker_attributes_transform() -> None:
    """Extra attributes are normalized for Home Assistant."""
    pet = {
        "petID": 1,
        "petName": "Rex",
        "batteryLevel": "90",
        "imageCloudURL": "http://image",
        "expired_days": -2,
        "petKind": "4",
    }
    coordinator = MagicMock()
    coordinator.data = {
        "gps_latitude": 1.0,
        "gps_longitude": 2.0,
        "gps_accuracy": 3,
        "gps_altitude": 4,
    }
    coordinator.async_add_listener = MagicMock()
    tracker = KippyPetTracker(coordinator, pet)
    attrs = tracker.extra_state_attributes
    assert attrs["battery"] == "90"
    assert "batteryLevel" not in attrs
    assert attrs["latitude"] == 1.0 and "gps_latitude" not in attrs
    assert attrs["longitude"] == 2.0 and "gps_longitude" not in attrs
    assert attrs["gps_accuracy"] == 3 and "gps_accuracy" in attrs
    assert attrs["altitude"] == 4 and "gps_altitude" not in attrs
    assert attrs["expired_days"] == 2
    assert attrs["petType"] == PET_KIND_TO_TYPE["4"]
    assert attrs["picture"] == "http://image"
    assert tracker.entity_picture == "http://image"
    assert tracker.source_type.value == "gps"
    assert tracker.latitude == 1.0
    assert tracker.longitude == 2.0
    assert tracker.location_accuracy == 3
    assert tracker.altitude == 4
    assert tracker.battery_level == 90


@pytest.mark.asyncio
async def test_tracker_handles_invalid_values() -> None:
    """Invalid numeric values are ignored."""
    pet = {"petID": 1, "batteryLevel": "bad", "expired_days": "unknown"}
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.async_add_listener = MagicMock()
    tracker = KippyPetTracker(coordinator, pet)
    attrs = tracker.extra_state_attributes
    assert attrs["expired_days"] == "unknown"
    assert tracker.battery_level is None
    assert tracker.latitude is None
    assert tracker.longitude is None


@pytest.mark.asyncio
async def test_device_tracker_async_setup_entry_creates_entities() -> None:
    """async_setup_entry adds tracker entities for each pet."""
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
    assert len(entities) == 1
    assert isinstance(entities[0], KippyPetTracker)


@pytest.mark.asyncio
async def test_device_tracker_async_setup_entry_missing_map() -> None:
    """No trackers added when map coordinator is missing."""
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
    async_add_entities.assert_called_once_with([])


@pytest.mark.asyncio
async def test_device_tracker_async_setup_entry_no_pets() -> None:
    """No trackers added when there are no pets."""
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
async def test_tracker_device_info_returns_identifiers() -> None:
    """Tracker exposes device identifiers from helper."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.async_add_listener = MagicMock()
    tracker = KippyPetTracker(coordinator, pet)
    info = tracker.device_info
    assert (DOMAIN, "1") in info["identifiers"]
