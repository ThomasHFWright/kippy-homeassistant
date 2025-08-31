"""Coordinator for Kippy data updates."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import KippyApi
from .const import DOMAIN

class KippyDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Kippy API."""

    def __init__(self, hass: HomeAssistant, api: KippyApi) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            hass.logger,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        await self.api.ensure_login()
        return {"pets": await self.api.get_pet_kippy_list()}
