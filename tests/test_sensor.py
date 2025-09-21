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
    KippyEnergySavingStatusSensor,
    KippyExpiredDaysSensor,
    KippyHomeDistanceSensor,
    KippyIDSensor,
    KippyIMEISensor,
    KippyLastContactSensor,
    KippyLastFixSensor,
    KippyLastGpsFixSensor,
    KippyLastLbsFixSensor,
    KippyLocalizationTechnologySensor,
    KippyNextContactSensor,
    KippyOperatingStatusSensor,
    KippyPetTypeSensor,
    KippyPlaySensor,
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


def test_expired_days_sensor_invalid_unit_of_measurement() -> None:
    """Invalid expired day values result in no native unit."""

    pet = {"petID": "1", "expired_days": "n/a"}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyExpiredDaysSensor(coordinator, pet)

    assert sensor.native_unit_of_measurement is None


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
    """Run sensor converts minutes to configured time unit and suggests hours."""
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
    assert sensor.suggested_unit_of_measurement == UnitOfTime.HOURS


def test_map_sensor_get_datetime_invalid() -> None:
    """Map-based sensors gracefully handle missing timestamps."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.data = None
    sensor = KippyLastContactSensor(coordinator, {"petID": 1})
    assert sensor.native_value is None

    coordinator.data = {"contact_time": "invalid"}
    assert sensor.native_value is None


def test_home_distance_sensor_handles_missing_coordinates(monkeypatch) -> None:
    """Distance sensor returns None for incomplete or invalid data."""

    hass = MagicMock()
    hass.config.units.length_unit = UnitOfLength.KILOMETERS
    hass.config.latitude = 0
    hass.config.longitude = 0

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyHomeDistanceSensor(coordinator, {"petID": 1})
    sensor.hass = hass

    coordinator.data = None
    assert sensor.native_value is None

    coordinator.data = {"gps_latitude": None, "gps_longitude": 0}
    assert sensor.native_value is None

    coordinator.data = {"gps_latitude": "a", "gps_longitude": "b"}
    assert sensor.native_value is None

    monkeypatch.setattr(
        "custom_components.kippy.sensor.location_distance", lambda *args, **kwargs: None
    )
    coordinator.data = {"gps_latitude": 0, "gps_longitude": 0}
    assert sensor.native_value is None


def test_activity_sensor_extra_state_none_without_data() -> None:
    """Activity sensor exposes no extra attributes until data is processed."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.get_activities.return_value = []
    sensor = KippyRunSensor(coordinator, {"petID": 1})

    assert sensor.extra_state_attributes is None


def test_activity_sensor_returns_none_when_value_missing() -> None:
    """Missing values result in None native state."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    coordinator.get_activities.return_value = [{"date": today, "run": None}]
    sensor = KippyRunSensor(coordinator, {"petID": 1})

    assert sensor.native_value is None


def test_activity_sensor_grouped_activities_filters_nonmatching() -> None:
    """Grouped activities sum values for the current day only."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyRunSensor(coordinator, {"petID": 1})
    today = datetime(2024, 1, 2, tzinfo=timezone.utc)
    activities = [
        {"activity": "walk", "data": []},
        {
            "activity": "run",
            "data": [
                {"timeCaption": "20230101", "valueMinutes": 2},
                {
                    "timeCaption": today.strftime("%Y%m%d") + "T1200",
                    "valueMinutes": 5,
                },
                {
                    "timeCaption": today.strftime("%Y%m%d") + "T1300",
                    "minutes": 3,
                },
            ],
        },
    ]

    total, date_str = sensor._value_from_grouped_activities(activities, today)
    assert total == 8.0
    assert date_str == "2024-01-02"


def test_activity_sensor_grouped_activities_no_match_returns_none() -> None:
    """Grouped data without the metric returns no value."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyRunSensor(coordinator, {"petID": 1})
    activities = [{"activity": "walk", "data": []}]

    total, date_str = sensor._value_from_grouped_activities(
        activities, datetime.now(timezone.utc)
    )
    assert total is None and date_str is None


def test_activity_sensor_daily_entries_nested_list() -> None:
    """Daily entries handle nested activity lists and dictionaries."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyRunSensor(coordinator, {"petID": 1})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    activities = [
        {"date": "1999-01-01", "run": 5},
        {
            "date": today,
            "run": None,
            "activities": [
                {"name": "run", "value": {"minutes": 7}},
            ],
        },
    ]

    value, date_str = sensor._value_from_daily_entries(
        activities, datetime.now(timezone.utc)
    )
    assert value == 7
    assert date_str == today


def test_activity_sensor_daily_entries_no_match_returns_none() -> None:
    """Daily entries return None when no data matches today."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyRunSensor(coordinator, {"petID": 1})
    activities = [{"date": "1999-01-01", "run": 5}]
    value, date_str = sensor._value_from_daily_entries(
        activities, datetime.now(timezone.utc)
    )
    assert value is None and date_str is None


def test_activity_sensor_extract_helpers() -> None:
    """Helper methods extract dates and first-present values."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyRunSensor(coordinator, {"petID": 1})

    assert sensor._extract_date({"foo": "bar"}) is None
    assert sensor._extract_first_present({"count": 3}, ("value", "count")) == 3


def test_activity_sensor_activity_list_missing_metric_returns_none() -> None:
    """Activity lists without the metric return None."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyRunSensor(coordinator, {"petID": 1})
    assert sensor._value_from_activity_list([{"name": "walk"}]) is None


def test_activity_sensor_extract_first_present_returns_none() -> None:
    """Missing keys result in None for first-present extraction."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyRunSensor(coordinator, {"petID": 1})
    assert sensor._extract_first_present({}, ("value", "count")) is None


def test_activity_sensor_extract_numeric_invalid() -> None:
    """Invalid numeric values are ignored."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyRunSensor(coordinator, {"petID": 1})
    data = {"value": "bad", "count": "also bad"}
    assert sensor._extract_numeric_value(data, ("value", "count")) is None


def test_activity_sensor_convert_invalid_value() -> None:
    """Non-numeric activity values are ignored."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    sensor = KippyStepsSensor(coordinator, {"petID": 1})
    assert sensor._convert_activity_value("invalid") is None


def test_activity_sensor_native_value_grouped_missing_metric() -> None:
    """Grouped activity payloads without the metric return ``None``."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.get_activities = MagicMock(
        return_value=[{"activity": "walk", "data": []}]
    )
    sensor = KippyRunSensor(coordinator, {"petID": 1})

    assert sensor.native_value is None


def test_activity_sensor_native_value_daily_missing_metric() -> None:
    """Daily entries without metric data also return ``None``."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    coordinator.get_activities = MagicMock(
        return_value=[{"date": today, "activities": [{"name": "walk"}]}]
    )
    sensor = KippyRunSensor(coordinator, {"petID": 1})

    assert sensor.native_value is None


def test_activity_sensor_native_value_daily_missing_keys() -> None:
    """Daily entries with empty dictionaries return ``None`` after extraction."""

    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    coordinator.get_activities = MagicMock(return_value=[{"date": today, "run": {}}])
    sensor = KippyRunSensor(coordinator, {"petID": 1})

    assert sensor.native_value is None


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
    assert any(isinstance(e, KippyPlaySensor) for e in entities)


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
