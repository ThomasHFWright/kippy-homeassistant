from unittest.mock import MagicMock

import pytest

from custom_components.kippy.const import OPERATING_STATUS, OPERATING_STATUS_MAP
from custom_components.kippy.switch import KippyEnergySavingSwitch


@pytest.mark.asyncio
async def test_energy_saving_switch_updates_from_operating_status() -> None:
    """Energy saving switch turns on when operating status is energy saving."""
    pet = {"petID": "1", "energySavingMode": 0}

    coordinator = MagicMock()
    coordinator.data = {"pets": [pet]}
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    map_coordinator = MagicMock()
    map_coordinator.data = {
        "operating_status": OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
    }
    map_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    switch = KippyEnergySavingSwitch(coordinator, pet, map_coordinator)
    switch.async_write_ha_state = MagicMock()

    assert not switch.is_on

    switch._handle_map_update()

    assert switch.is_on
    assert pet["energySavingMode"] == 1

