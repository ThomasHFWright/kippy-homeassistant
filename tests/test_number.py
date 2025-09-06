from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.kippy.number import (
    KippyIdleUpdateFrequencyNumber,
    KippyLiveUpdateFrequencyNumber,
    KippyUpdateFrequencyNumber,
)


@pytest.mark.asyncio
async def test_update_frequency_number() -> None:
    """Ensure native value and setting value update pet data."""
    pet = {"petID": 1, "petName": "Rex", "updateFrequency": 5}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    number = KippyUpdateFrequencyNumber(coordinator, pet)
    assert number.native_value == 5.0
    number.async_write_ha_state = MagicMock()
    await number.async_set_native_value(10)
    assert pet["updateFrequency"] == 10
    number.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_update_frequency_number_missing() -> None:
    """Missing updateFrequency returns None."""
    pet = {"petID": 1}
    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock()
    number = KippyUpdateFrequencyNumber(coordinator, pet)
    assert number.native_value is None


@pytest.mark.asyncio
async def test_idle_and_live_numbers() -> None:
    """Idle and live numbers interact with coordinator."""
    pet = {"petID": 1, "petName": "Rex"}
    map_coordinator = MagicMock()
    map_coordinator.idle_refresh = 300
    map_coordinator.live_refresh = 10
    map_coordinator.async_set_idle_refresh = AsyncMock()
    map_coordinator.async_set_live_refresh = AsyncMock()
    map_coordinator.async_add_listener = MagicMock()

    idle = KippyIdleUpdateFrequencyNumber(map_coordinator, pet)
    live = KippyLiveUpdateFrequencyNumber(map_coordinator, pet)
    assert idle.native_value == 5.0
    assert live.native_value == 10.0
    idle.async_write_ha_state = MagicMock()
    live.async_write_ha_state = MagicMock()
    await idle.async_set_native_value(6)
    await live.async_set_native_value(7)
    map_coordinator.async_set_idle_refresh.assert_called_once_with(360)
    map_coordinator.async_set_live_refresh.assert_called_once_with(7)
    idle.async_write_ha_state.assert_called_once()
    live.async_write_ha_state.assert_called_once()
