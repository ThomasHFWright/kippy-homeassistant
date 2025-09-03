import logging
from unittest.mock import MagicMock
from pathlib import Path
import sys

import pytest
from homeassistant.core import HomeAssistant

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.kippy.const import PET_KIND_TO_TYPE
from custom_components.kippy.sensor import KippyExpiredDaysSensor, KippyPetTypeSensor


@pytest.mark.asyncio
async def test_expired_days_sensor_returns_expired(hass: HomeAssistant) -> None:
    """Ensure non-negative days report as 'Expired'."""
    pet = {"petID": "1", "expired_days": 0}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyExpiredDaysSensor(coordinator, pet)

    assert sensor.native_value == "Expired"

    pet["expired_days"] = 5
    assert sensor.native_value == "Expired"


@pytest.mark.asyncio
async def test_expired_days_sensor_returns_positive_days(hass: HomeAssistant) -> None:
    """Negative days are returned as positive remaining days."""
    pet = {"petID": "1", "expired_days": -3}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyExpiredDaysSensor(coordinator, pet)

    assert sensor.native_value == 3


@pytest.mark.asyncio
async def test_pet_type_sensor_maps_kind_to_type(hass: HomeAssistant) -> None:
    """Pet type sensor should map kind code to type label."""
    pet = {"petID": "1", "petKind": "4"}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    sensor = KippyPetTypeSensor(coordinator, pet)

    assert sensor.native_value == PET_KIND_TO_TYPE["4"]
