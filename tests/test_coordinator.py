import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.kippy.const import (
    LOCALIZATION_TECHNOLOGY_LBS,
    OPERATING_STATUS,
    OPERATING_STATUS_MAP,
)
from custom_components.kippy.coordinator import (
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)


@pytest.mark.asyncio
async def test_process_new_data_maps_operating_status() -> None:
    """process_new_data should map numeric operating status codes."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coordinator = KippyMapDataUpdateCoordinator(hass, MagicMock(), MagicMock(), 1)

    coordinator.process_new_data({"operating_status": OPERATING_STATUS.ENERGY_SAVING})

    assert (
        coordinator.data["operating_status"]
        == OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    )


@pytest.mark.asyncio
async def test_data_coordinator_update_success() -> None:
    """_async_update_data returns pets list on success."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    api = MagicMock()
    api.get_pet_kippy_list = AsyncMock(return_value=[{"petID": 1}])
    coordinator = KippyDataUpdateCoordinator(hass, MagicMock(), api)
    data = await coordinator._async_update_data()
    assert data == {"pets": [{"petID": 1}]}


@pytest.mark.asyncio
async def test_data_coordinator_update_failure() -> None:
    """UpdateFailed is raised when API call fails."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    api = MagicMock()
    api.get_pet_kippy_list = AsyncMock(side_effect=Exception)
    coordinator = KippyDataUpdateCoordinator(hass, MagicMock(), api)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_map_coordinator_process_data_ignores_lbs() -> None:
    """LBS data is ignored and previous GPS data reused."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coord = KippyMapDataUpdateCoordinator(hass, MagicMock(), MagicMock(), 1)
    coord.ignore_lbs = True
    coord.data = {"gps_latitude": 5, "gps_longitude": 6}
    data = {
        "localization_technology": LOCALIZATION_TECHNOLOGY_LBS,
        "gps_latitude": 1,
        "gps_longitude": 2,
    }
    processed = coord._process_data(data)
    assert processed["gps_latitude"] == 5 and processed["gps_longitude"] == 6


@pytest.mark.asyncio
async def test_map_coordinator_set_refresh_updates_interval() -> None:
    """Setting refresh values updates coordinator interval based on status."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    coord = KippyMapDataUpdateCoordinator(hass, MagicMock(), MagicMock(), 1)
    coord.data = {"operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]}
    await coord.async_set_live_refresh(20)
    assert coord.update_interval == timedelta(seconds=20)
    coord.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    }
    await coord.async_set_idle_refresh(600)
    assert coord.update_interval == timedelta(seconds=600)
