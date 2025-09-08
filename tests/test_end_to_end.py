import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kippy.const import DOMAIN, OPERATING_STATUS, PET_KIND_TO_TYPE


@pytest.mark.asyncio
async def test_pet_setup_end_to_end(
    hass: HomeAssistant, enable_custom_integrations
) -> None:
    """Test full integration setup and sensor values for a pet."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    now = datetime.utcnow()
    ts = int(now.timestamp())

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
    api.get_activity_categories.assert_awaited_once()

    data = hass.data[DOMAIN][entry.entry_id]
    assert set(data["map_coordinators"].keys()) == {1}

    expected_states = {
        "sensor.rex_days_until_expiry": "5",
        "sensor.rex_kippy_id": "123",
        "sensor.rex_imei": "ABC",
        "sensor.rex_type": PET_KIND_TO_TYPE["4"],
        "sensor.rex_battery_level": "80",
        "sensor.rex_localization_technology": "GPS",
        "sensor.rex_last_contact": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
        "sensor.rex_last_fix": datetime.fromtimestamp(ts - 1, timezone.utc).isoformat(),
        "sensor.rex_last_gps_fix": datetime.fromtimestamp(ts - 2, timezone.utc).isoformat(),
        "sensor.rex_last_lbs_fix": datetime.fromtimestamp(ts - 3, timezone.utc).isoformat(),
        "sensor.rex_operating_status": "idle",
        "sensor.rex_steps": "1000",
        "sensor.rex_calories": "200",
        "sensor.rex_run": "10",
        "sensor.rex_walk": "20",
        "sensor.rex_sleep": "30",
        "sensor.rex_rest": "40",
    }

    for entity_id, value in expected_states.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"Missing entity {entity_id}"
        assert state.state == value

    assert hass.states.get("sensor.old_days_until_expiry").state == "Expired"
    assert hass.states.get("sensor.old_battery_level") is None
    assert hass.states.get("sensor.old_steps") is None
