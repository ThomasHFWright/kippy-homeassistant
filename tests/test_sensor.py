from datetime import datetime, timezone
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
    KippyBatterySensor,
    KippyContactTimeSensor,
    KippyNextCallTimeSensor,
    KippyExpiredDaysSensor,
    KippyFixTimeSensor,
    KippyGpsTimeSensor,
    KippyIDSensor,
    KippyIMEISensor,
    KippyLbsTimeSensor,
    KippyLocalizationTechnologySensor,
    KippyOperatingStatusSensor,
    KippyPetTypeSensor,
    KippyStepsSensor,
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
    assert sensor.device_info["name"] == "Kippy"


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
    assert any(isinstance(e, KippyNextCallTimeSensor) for e in entities)


@pytest.mark.asyncio
async def test_sensor_async_setup_entry_expired_pet_only_basic_sensors() -> None:
    """Expired pets only expose basic diagnostic sensors."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "1"
    coordinator = MagicMock()
    coordinator.data = {
        "pets": [
            {"petID": 1, "kippyID": 1, "kippyIMEI": "a", "expired_days": -1},
            {"petID": 2, "kippyID": 2, "kippyIMEI": "b", "expired_days": 0},
        ]
    }
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
    entities = async_add_entities.call_args[0][0]
    expired_entities = [e for e in entities if getattr(e, "_pet_id", None) == 2]
    assert len(expired_entities) == 3
    assert {type(e) for e in expired_entities} == {
        KippyExpiredDaysSensor,
        KippyIDSensor,
        KippyIMEISensor,
    }


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


def test_base_entity_updates_and_device_info() -> None:
    """_handle_coordinator_update refreshes pet data and device info."""
    pet1 = {"petID": 1, "petName": "Rex", "kippyID": 2}
    coord = MagicMock()
    coord.data = {"pets": [pet1]}
    coord.async_add_listener = MagicMock()
    sensor = KippyIDSensor(coord, pet1)
    sensor.hass = MagicMock()
    sensor.entity_id = "sensor.test"
    coord.data = {"pets": [{"petID": 1, "petName": "Max", "kippyID": 3}]}
    sensor.async_write_ha_state = MagicMock()
    sensor._handle_coordinator_update()
    sensor.async_write_ha_state.assert_called_once()
    assert sensor.device_info["name"] == "Kippy Max"
    assert sensor.native_value == 3


def test_expired_days_invalid_and_none() -> None:
    """Expired days sensor handles invalid values."""
    pet = {"petID": 1, "expired_days": "bad"}
    coord = MagicMock()
    coord.data = {"pets": [pet]}
    coord.async_add_listener = MagicMock()
    sensor = KippyExpiredDaysSensor(coord, pet)
    assert sensor.native_value is None
    pet["expired_days"] = None
    assert sensor.native_value is None


def test_imei_sensor_and_battery_sensor() -> None:
    """IMEI and battery sensors expose data."""
    pet = {"petID": 1, "kippyIMEI": "abc", "battery": "50"}
    coord = MagicMock()
    coord.data = {"gps_time": 1, "battery": 60}
    sensor_batt = KippyBatterySensor(coord, pet)
    assert sensor_batt.native_value == 60
    coord.data = {}
    assert sensor_batt.native_value == 50
    pet_bad = {"petID": 2, "battery": "bad"}
    sensor_batt2 = KippyBatterySensor(coord, pet_bad)
    assert sensor_batt2.native_value is None
    sensor_imei = KippyIMEISensor(coord, pet)
    assert sensor_imei.native_value == "abc"


def test_localization_and_time_sensors() -> None:
    """Map-based sensors convert timestamps."""
    coord = MagicMock()
    coord.data = {
        "localization_technology": "GPS",
        "contact_time": 1,
        "fix_time": "bad",
        "gps_time": 2,
        "lbs_time": 3,
    }
    pet = {"petID": 1, "petName": "Rex"}
    loc = KippyLocalizationTechnologySensor(coord, pet)
    assert loc.native_value == "GPS"
    assert loc.device_info["name"] == "Kippy Rex"
    contact = KippyContactTimeSensor(coord, pet)
    assert contact.native_value == datetime.utcfromtimestamp(1).replace(
        tzinfo=timezone.utc
    )
    assert contact.device_info["name"] == "Kippy Rex"
    fix = KippyFixTimeSensor(coord, pet)
    assert fix.native_value is None
    gps = KippyGpsTimeSensor(coord, pet)
    assert gps.native_value == datetime.utcfromtimestamp(2).replace(tzinfo=timezone.utc)
    lbs = KippyLbsTimeSensor(coord, pet)
    assert lbs.native_value == datetime.utcfromtimestamp(3).replace(tzinfo=timezone.utc)


def test_next_call_time_sensor_native_value() -> None:
    """Next call time uses contact time and update frequency."""
    coord = MagicMock()
    coord.data = {"contact_time": 10}
    pet = {"petID": 1, "petName": "Rex", "updateFrequency": 5}
    sensor = KippyNextCallTimeSensor(coord, pet)
    assert sensor.native_value == datetime.fromtimestamp(10 + 5 * 3600, timezone.utc)

    coord.data = {"contact_time": None}
    assert sensor.native_value is None

    coord.data = {"contact_time": 10}
    pet["updateFrequency"] = None
    assert sensor.native_value is None

    pet["updateFrequency"] = "bad"
    assert sensor.native_value is None


def test_activity_sensor_handles_cat_and_dog_data() -> None:
    """Activity sensor parses both cat-style and dog-style payloads."""
    api_coord = MagicMock()
    api_coord.get_activities = MagicMock()
    coord = MagicMock()
    today = datetime.utcnow()
    today_code = today.strftime("%Y%m%d")
    coord.get_activities = MagicMock(
        return_value=[
            {"activity": "other", "data": []},
            {"activity": "steps", "data": [{"timeCaption": today_code, "value": "5"}]},
        ]
    )
    sensor = KippyStepsSensor(coord, {"petID": 1, "petName": "Rex"})
    assert sensor.native_value == 5
    assert sensor.device_info["name"] == "Kippy Rex"
    assert sensor.extra_state_attributes == {"date": today.strftime("%Y-%m-%d")}

    coord.get_activities.return_value = [
        {"date": today.strftime("%Y-%m-%d"), "steps": "7"}
    ]
    sensor._date = None
    assert sensor.native_value == 7

    coord.get_activities.return_value = None
    assert sensor.native_value is None
