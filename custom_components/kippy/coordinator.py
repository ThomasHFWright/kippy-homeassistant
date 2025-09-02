"""Coordinator for Kippy data updates."""
from __future__ import annotations

import logging

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import KippyApi
from .const import (
    DOMAIN,
    LOCALIZATION_TECHNOLOGY_LBS,
    OPERATING_STATUS_LIVE,
)

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
        self.ignore_lbs = True
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{kippy_id}_map",
            update_interval=timedelta(seconds=self.idle_refresh),
        )

    async def _async_update_data(self):
        """Fetch location data and adjust the refresh interval."""
        data = await self.api.kippymap_action(self.kippy_id)
        if (
            self.ignore_lbs
            and data.get("localization_technology") == LOCALIZATION_TECHNOLOGY_LBS
        ):
            _LOGGER.debug("Ignoring LBS location update for %s", self.kippy_id)
            if self.data:
                for key in (
                    "gps_latitude",
                    "gps_longitude",
                    "gps_accuracy",
                    "gps_altitude",
                ):
                    if key in self.data:
                        data[key] = self.data[key]
                    else:
                        data.pop(key, None)
            else:
                for key in (
                    "gps_latitude",
                    "gps_longitude",
                    "gps_accuracy",
                    "gps_altitude",
                ):
                    data.pop(key, None)

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


class KippyActivityCategoriesDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch activity category information."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: KippyApi,
        pet_ids: list[int],
        update_hours: int = 6,
    ) -> None:
        """Initialize the activity categories coordinator."""
        self.api = api
        self.pet_ids = pet_ids
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_activities",
            update_interval=timedelta(hours=update_hours),
        )

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch activity categories for all configured pets."""
        now = datetime.utcnow()
        from_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")
        data: dict[int, dict[str, Any]] = {}
        for pet_id in self.pet_ids:
            data[pet_id] = await self.api.get_activity_categories(
                pet_id, from_date, to_date, 1, 1
            )
        return data

    async def async_refresh_pet(self, pet_id: int) -> None:
        """Manually refresh activity data for a single pet."""
        now = datetime.utcnow()
        from_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")
        result = await self.api.get_activity_categories(pet_id, from_date, to_date, 1, 1)
        new_data = dict(self.data or {})
        new_data[pet_id] = result
        self.async_set_updated_data(new_data)

    def get_activities(self, pet_id: int):
        """Return cached activities for the given pet."""
        return (self.data or {}).get(pet_id, {}).get("activities")

    def get_avg(self, pet_id: int):
        """Return cached averages for the given pet."""
        return (self.data or {}).get(pet_id, {}).get("avg")

    def get_health(self, pet_id: int):
        """Return cached health information for the given pet."""
        return (self.data or {}).get(pet_id, {}).get("health")
