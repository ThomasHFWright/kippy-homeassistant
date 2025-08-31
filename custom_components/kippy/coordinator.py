"""Coordinator for Kippy data updates."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import KippyApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class KippyDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Kippy API."""

    def __init__(self, hass: HomeAssistant, api: KippyApi) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Fetching the pet list does not need to happen on a schedule.
            # The coordinator will only update when explicitly requested.
            update_interval=None,
        )

    async def _async_update_data(self):
        """Fetch data from the API endpoint."""
        # ``get_pet_kippy_list`` internally ensures a valid login session.
        return {"pets": await self.api.get_pet_kippy_list()}
