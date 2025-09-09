from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.util.location import distance as location_distance
from homeassistant.util.unit_conversion import DistanceConverter, DurationConverter

from custom_components.kippy.const import (
    DOMAIN,
    LABEL_EXPIRED,
    OPERATING_STATUS,
    OPERATING_STATUS_MAP,
    PET_KIND_TO_TYPE,
)
from custom_components.kippy.sensor import (
    KippyBatterySensor,
    KippyLastContactSensor,
    KippyNextContactSensor,
    KippyExpiredDaysSensor,
    KippyLastFixSensor,
    KippyLastGpsFixSensor,
    KippyIDSensor,
    KippyIMEISensor,
    KippyLastLbsFixSensor,
    KippyLocalizationTechnologySensor,
    KippyOperatingStatusSensor,
    KippyEnergySavingStatusSensor,
    KippyHomeDistanceSensor,
    KippyPetTypeSensor,
    KippyRunSensor,
    KippyStepsSensor,
    async_setup_entry,
)
from custom_components.kippy.switch import KippyEnergySavingSwitch


@pytest.mark.asyncio
async def test_expired_days_sensor_returns_expired() -> None:
    """Ensure non-negative days report as 'Expired'."""
    pet = {"petID": "1", "expired_days": 0}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyExpiredDaysSensor(coordinator, pet)
    hass = MagicMock()
    hass.config.units.get_converted_unit.return_value = None
    sensor.hass = hass

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
    hass = MagicMock()
    hass.config.units.get_converted_unit.return_value = None
    sensor.hass = hass

    assert sensor.native_value == 3


@pytest.mark.asyncio
async def test_expired_days_sensor_uses_configured_unit() -> None:
    """Expired days sensor converts to configured time unit."""
    pet = {"petID": "1", "expired_days": -2}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyExpiredDaysSensor(coordinator, pet)
    hass = MagicMock()
    hass.config.units.get_converted_unit.return_value = UnitOfTime.HOURS
    sensor.hass = hass
    expected = DurationConverter.convert(2, UnitOfTime.DAYS, UnitOfTime.HOURS)
    assert sensor.native_unit_of_measurement == UnitOfTime.HOURS
    assert sensor.native_value == expected


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
async def test_home_distance_sensor_calculates_distance() -> None:
    """Home distance sensor should calculate distance in meters."""
    hass = MagicMock()
    hass.config.units.length_unit = UnitOfLength.KILOMETERS
    hass.config.latitude = 0
    hass.config.longitude = 0
    coordinator = MagicMock()
    coordinator.data = {"gps_latitude": 0, "gps_longitude": 1}
    sensor = KippyHomeDistanceSensor(coordinator, {"petID": "1"})
    sensor.hass = hass
    expected_m = location_distance(0, 0, 0, 1)
    expected = DistanceConverter.convert(
        expected_m, UnitOfLength.METERS, UnitOfLength.METERS
    )
    assert sensor.native_value == pytest.approx(expected)
    assert sensor.native_unit_of_measurement == UnitOfLength.METERS


@pytest.mark.asyncio
async def test_home_distance_sensor_uses_configured_unit() -> None:
    """Distance sensor converts to configured length unit."""
    hass = MagicMock()
    hass.config.units.length_unit = UnitOfLength.MILES
    hass.config.latitude = 0
    hass.config.longitude = 0
    coordinator = MagicMock()
    coordinator.data = {"gps_latitude": 0, "gps_longitude": 1}
    sensor = KippyHomeDistanceSensor(coordinator, {"petID": "1"})
    sensor.hass = hass
    expected_m = location_distance(0, 0, 0, 1)
    expected = DistanceConverter.convert(
        expected_m, UnitOfLength.METERS, UnitOfLength.MILES
    )
    assert sensor.native_value == pytest.approx(expected)
    assert sensor.native_unit_of_measurement == UnitOfLength.MILES


@pytest.mark.asyncio
async def test_run_sensor_uses_configured_unit() -> None:
    """Run sensor converts minutes to configured time unit."""
    hass = MagicMock()
    hass.config.units.get_converted_unit.return_value = UnitOfTime.HOURS
    coord = MagicMock()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    coord.get_activities.return_value = [{"date": today, "run": 60}]
    sensor = KippyRunSensor(coord, {"petID": 1})
    sensor.hass = hass
    expected = DurationConverter.convert(60, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    assert sensor.native_unit_of_measurement == UnitOfTime.HOURS
    assert sensor.native_value == expected


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
    assert any(isinstance(e, KippyNextContactSensor) for e in entities)
    assert any(isinstance(e, KippyHomeDistanceSensor) for e in entities)


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
    hass = MagicMock()
    hass.config.units.get_converted_unit.return_value = None
    sensor.hass = hass
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
    contact = KippyLastContactSensor(coord, pet)
    assert contact.native_value == datetime.utcfromtimestamp(1).replace(
        tzinfo=timezone.utc
    )
    assert contact.device_info["name"] == "Kippy Rex"
    fix = KippyLastFixSensor(coord, pet)
    assert fix.native_value is None
    gps = KippyLastGpsFixSensor(coord, pet)
    assert gps.native_value == datetime.utcfromtimestamp(2).replace(tzinfo=timezone.utc)
    lbs = KippyLastLbsFixSensor(coord, pet)
    assert lbs.native_value == datetime.utcfromtimestamp(3).replace(tzinfo=timezone.utc)


def test_next_contact_sensor_native_value() -> None:
    """Next contact uses contact time and update frequency."""
    coord = MagicMock()
    coord.data = {"contact_time": 10}
    base_coord = MagicMock()
    pet = {"petID": 1, "petName": "Rex", "updateFrequency": 5}
    base_coord.data = {"pets": [pet]}

    def add_listener(cb):
        base_coord.listener = cb
        return MagicMock()

    base_coord.async_add_listener.side_effect = add_listener
    sensor = KippyNextContactSensor(coord, base_coord, pet)
    assert sensor.native_value == datetime.fromtimestamp(10 + 5 * 3600, timezone.utc)

    coord.data = {"contact_time": None}
    assert sensor.native_value is None

    coord.data = {"contact_time": 10}
    pet["updateFrequency"] = None
    assert sensor.native_value is None

    pet["updateFrequency"] = "bad"
    assert sensor.native_value is None


def test_next_contact_sensor_updates_on_frequency_change() -> None:
    """Sensor updates when the GPS update frequency changes."""
    coord = MagicMock()
    coord.data = {"contact_time": 10}
    base_coord = MagicMock()
    pet = {"petID": 1, "petName": "Rex", "updateFrequency": 5}
    base_coord.data = {"pets": [pet]}

    def add_listener(cb):
        base_coord.listener = cb
        return MagicMock()

    base_coord.async_add_listener.side_effect = add_listener
    sensor = KippyNextContactSensor(coord, base_coord, pet)
    sensor.hass = MagicMock()
    sensor.async_write_ha_state = MagicMock()
    assert sensor.native_value == datetime.fromtimestamp(10 + 5 * 3600, timezone.utc)

    pet["updateFrequency"] = 6
    base_coord.data = {"pets": [pet]}
    base_coord.listener()
    assert sensor.native_value == datetime.fromtimestamp(10 + 6 * 3600, timezone.utc)


def test_activity_sensor_handles_cat_and_dog_data() -> None:
    """Activity sensor parses both cat-style and dog-style payloads."""
    api_coord = MagicMock()
    api_coord.get_activities = MagicMock()
    coord = MagicMock()
    today = datetime.now(timezone.utc)
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


@pytest.mark.asyncio
async def test_energy_saving_status_sensor_pending_and_updates() -> None:
    """Energy saving status sensor reflects pending and confirmed states."""
    pet = {"petID": "1", "energySavingMode": 0, "kippyID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    coordinator.api.modify_kippy_settings = AsyncMock()
    coordinator.async_set_updated_data = MagicMock()
    map_coordinator = MagicMock()
    map_coordinator.data = {}
    map_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    switch = KippyEnergySavingSwitch(coordinator, pet, map_coordinator)
    switch.async_write_ha_state = MagicMock()
    sensor = KippyEnergySavingStatusSensor(coordinator, pet)

    assert sensor.native_value == "off"

    await switch.async_turn_on()
    assert sensor.native_value == "on_pending"

    map_coordinator.data["operating_status"] = OPERATING_STATUS_MAP[
        OPERATING_STATUS.ENERGY_SAVING
    ]
    switch._handle_map_update()
    assert sensor.native_value == "on"

    await switch.async_turn_off()
    assert sensor.native_value == "off_pending"

    switch._handle_map_update()
    assert sensor.native_value == "off_pending"

    map_coordinator.data["operating_status"] = OPERATING_STATUS_MAP[
        OPERATING_STATUS.IDLE
    ]
    switch._handle_map_update()
    assert sensor.native_value == "off"


@pytest.mark.asyncio
async def test_energy_saving_status_sensor_cancel_pending() -> None:
    """Toggling again cancels pending state for energy saving status sensor."""
    pet = {"petID": "1", "energySavingMode": 0, "kippyID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    coordinator.api.modify_kippy_settings = AsyncMock()
    coordinator.async_set_updated_data = MagicMock()
    map_coordinator = MagicMock()
    map_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    switch = KippyEnergySavingSwitch(coordinator, pet, map_coordinator)
    switch.async_write_ha_state = MagicMock()
    sensor = KippyEnergySavingStatusSensor(coordinator, pet)

    await switch.async_turn_on()
    assert sensor.native_value == "on_pending"

    await switch.async_turn_off()
    assert sensor.native_value == "off"

    await switch.async_turn_off()
    assert sensor.native_value == "off_pending"

    await switch.async_turn_on()
    assert sensor.native_value == "on"
