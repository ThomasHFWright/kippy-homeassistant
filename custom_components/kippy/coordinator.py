"""Coordinator for Kippy data updates."""
from __future__ import annotations

import logging

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import KippyApi
from .const import DOMAIN, OPERATING_STATUS_LIVE

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


class KippyMapDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for periodic ``kippymap_action`` calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: KippyApi,
        kippy_id: int,
        idle_refresh: int = 300,
        live_refresh: int = 10,
    ) -> None:
        """Initialize the map coordinator."""
        self.api = api
        self.kippy_id = kippy_id
        self.idle_refresh = idle_refresh
        self.live_refresh = live_refresh
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{kippy_id}_map",
            update_interval=timedelta(seconds=self.idle_refresh),
        )

    async def _async_update_data(self):
        """Fetch location data and adjust the refresh interval."""
        data = await self.api.kippymap_action(self.kippy_id)
        operating_status = data.get("operating_status")
        try:
            operating_status = int(operating_status)
        except (TypeError, ValueError):
            operating_status = None
        if operating_status == OPERATING_STATUS_LIVE:
            self.update_interval = timedelta(seconds=self.live_refresh)
        else:
            self.update_interval = timedelta(seconds=self.idle_refresh)
        return data

    async def async_set_idle_refresh(self, value: int) -> None:
        """Update idle refresh value and interval when idle."""
        self.idle_refresh = value
        if self.data:
            operating_status = self.data.get("operating_status")
            try:
                operating_status = int(operating_status)
            except (TypeError, ValueError):
                operating_status = None
            if operating_status != OPERATING_STATUS_LIVE:
                self.update_interval = timedelta(seconds=self.idle_refresh)

    async def async_set_live_refresh(self, value: int) -> None:
        """Update live refresh value and interval when live."""
        self.live_refresh = value
        if self.data:
            operating_status = self.data.get("operating_status")
            try:
                operating_status = int(operating_status)
            except (TypeError, ValueError):
                operating_status = None
            if operating_status == OPERATING_STATUS_LIVE:
                self.update_interval = timedelta(seconds=self.live_refresh)
