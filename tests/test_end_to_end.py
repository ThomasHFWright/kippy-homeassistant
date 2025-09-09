from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_conversion import DurationConverter
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kippy.const import DOMAIN, OPERATING_STATUS, PET_KIND_TO_TYPE


@pytest.mark.asyncio
async def test_pet_setup_end_to_end(
    hass: HomeAssistant, enable_custom_integrations
) -> None:
    """Test full integration setup and sensor values for a pet."""
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    ts = int(today.timestamp())

    pets = [
        {
            "petID": 1,
            "petName": "Rex",
            "kippyID": 123,
            "kippyIMEI": "ABC",
            "expired_days": -5,
            "petKind": "4",
        },
        {
            "petID": 2,
            "petName": "Old",
            "kippyID": 456,
            "kippyIMEI": "DEF",
            "expired_days": 0,
        },
    ]

    map_data = {
        "battery": 80,
        "localization_technology": "GPS",
        "contact_time": ts,
        "fix_time": ts - 1,
        "gps_time": ts - 2,
        "lbs_time": ts - 3,
        "gps_latitude": 1.0,
        "gps_longitude": 2.0,
        "gps_accuracy": 3,
        "gps_altitude": 4,
        "operating_status": OPERATING_STATUS.IDLE,
    }

    activity_data = {
        "activities": [
            {
                "date": today_str,
                "steps": 1000,
                "calories": 200,
                "run": 10,
                "walk": 20,
                "sleep": 30,
                "rest": 40,
                "play": 50,
                "relax": 60,
                "jumps": 70,
                "climb": 80,
                "grooming": 90,
                "eat": 100,
                "drink": 110,
            }
        ]
    }

    api = AsyncMock()
    api.login = AsyncMock()
    api.get_pet_kippy_list = AsyncMock(return_value=pets)
    api.kippymap_action = AsyncMock(return_value=map_data)
    api.get_activity_categories = AsyncMock(return_value=activity_data)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "a", CONF_PASSWORD: "b"},
    )
    entry.add_to_hass(hass)

    with patch("custom_components.kippy.aiohttp_client.async_get_clientsession"), patch(
        "custom_components.kippy.KippyApi.async_create", return_value=api
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    api.login.assert_awaited_once_with("a", "b")
    api.get_pet_kippy_list.assert_awaited_once()
    api.kippymap_action.assert_awaited_once_with(123)
    api.get_activity_categories.assert_awaited_once_with(
        1, today_str, (today + timedelta(days=1)).strftime("%Y-%m-%d"), 2, 1
    )

    data = hass.data[DOMAIN][entry.entry_id]
    assert set(data["map_coordinators"].keys()) == {1}

    run = DurationConverter.convert(10, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    walk = DurationConverter.convert(20, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    sleep = DurationConverter.convert(30, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    rest = DurationConverter.convert(40, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    play = DurationConverter.convert(50, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    relax = DurationConverter.convert(60, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    climb = DurationConverter.convert(80, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    grooming = DurationConverter.convert(90, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    eat = DurationConverter.convert(100, UnitOfTime.MINUTES, UnitOfTime.HOURS)
    drink = DurationConverter.convert(110, UnitOfTime.MINUTES, UnitOfTime.HOURS)

    expected_states = {
        "sensor.rex_days_until_expiry": "5",
        "sensor.rex_kippy_id": "123",
        "sensor.rex_imei": "ABC",
        "sensor.rex_type": PET_KIND_TO_TYPE["4"],
        "sensor.rex_battery_level": "80",
        "sensor.rex_localization_technology": "GPS",
        "sensor.rex_last_contact": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
        "sensor.rex_last_fix": datetime.fromtimestamp(ts - 1, timezone.utc).isoformat(),
        "sensor.rex_last_gps_fix": datetime.fromtimestamp(
            ts - 2, timezone.utc
        ).isoformat(),
        "sensor.rex_last_lbs_fix": datetime.fromtimestamp(
            ts - 3, timezone.utc
        ).isoformat(),
        "sensor.rex_operating_status": "idle",
        "sensor.rex_steps": "1000",
        "sensor.rex_calories": "200",
        "sensor.rex_jumps": "70",
    }

    for entity_id, value in expected_states.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"Missing entity {entity_id}"
        assert state.state == value

    time_states = {
        "sensor.rex_run": run,
        "sensor.rex_walk": walk,
        "sensor.rex_sleep": sleep,
        "sensor.rex_rest": rest,
        "sensor.rex_play": play,
        "sensor.rex_relax": relax,
        "sensor.rex_climb": climb,
        "sensor.rex_grooming": grooming,
        "sensor.rex_eat": eat,
        "sensor.rex_drink": drink,
    }

    for entity_id, value in time_states.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"Missing entity {entity_id}"
        assert float(state.state) == pytest.approx(value)

    assert hass.states.get("sensor.old_days_until_expiry").state == "Expired"
    assert hass.states.get("sensor.old_battery_level") is None
    assert hass.states.get("sensor.old_steps") is None
