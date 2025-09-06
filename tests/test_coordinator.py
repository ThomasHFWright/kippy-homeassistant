import asyncio
from unittest.mock import MagicMock

import pytest

from custom_components.kippy.const import OPERATING_STATUS, OPERATING_STATUS_MAP
from custom_components.kippy.coordinator import KippyMapDataUpdateCoordinator


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
