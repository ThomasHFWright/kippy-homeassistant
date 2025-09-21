"""Coordinator for Kippy data updates."""

from __future__ import annotations

import inspect
import logging
from asyncio import TimeoutError as AsyncioTimeoutError
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from typing import Any, Callable

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import KippyApi
from .const import (
    DEFAULT_ACTIVITY_REFRESH_DELAY,
    DOMAIN,
    LOCALIZATION_TECHNOLOGY_LBS,
    OPERATING_STATUS,
    OPERATING_STATUS_MAP,
)

_LOGGER = logging.getLogger(__name__)

_HAS_CONFIG_ENTRY = (
    "config_entry" in inspect.signature(DataUpdateCoordinator.__init__).parameters
)


class KippyDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Kippy API."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, api: KippyApi
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.config_entry = config_entry
        kwargs: dict[str, Any] = {
            "name": DOMAIN,
            # Fetching the pet list does not need to happen on a schedule.
            # The coordinator will only update when explicitly requested.
            "update_interval": None,
        }
        if _HAS_CONFIG_ENTRY:
            kwargs["config_entry"] = config_entry
        super().__init__(hass, _LOGGER, **kwargs)

    async def _async_update_data(self):
        """Fetch data from the API endpoint."""
        # ``get_pet_kippy_list`` internally ensures a valid login session.
        try:
            return {"pets": await self.api.get_pet_kippy_list()}
        except (
            ClientError,
            AsyncioTimeoutError,
            RuntimeError,
            JSONDecodeError,
        ) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class KippyMapDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for periodic ``kippymap_action`` calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: KippyApi,
        kippy_id: int,
        idle_refresh: int = 300,
        live_refresh: int = 10,
    ) -> None:
        """Initialize the map coordinator."""
        self.api = api
        self.config_entry = config_entry
        self.kippy_id = kippy_id
        self.idle_refresh = idle_refresh
        self.live_refresh = live_refresh
        self.ignore_lbs = True
        kwargs: dict[str, Any] = {
            "name": f"{DOMAIN}_{kippy_id}_map",
            "update_interval": timedelta(seconds=self.idle_refresh),
        }
        if _HAS_CONFIG_ENTRY:
            kwargs["config_entry"] = config_entry
        super().__init__(hass, _LOGGER, **kwargs)

    async def _async_update_data(self):
        """Fetch location data and adjust the refresh interval."""
        try:
            data = await self.api.kippymap_action(self.kippy_id)
        except (
            ClientError,
            AsyncioTimeoutError,
            RuntimeError,
            JSONDecodeError,
        ) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        return self._process_data(data)

    def _process_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw kippymap data from the API."""
        if (
            self.ignore_lbs
            and data.get("localization_technology") == LOCALIZATION_TECHNOLOGY_LBS
        ):
            has_location = self.data and any(
                key in self.data for key in ("gps_latitude", "gps_longitude")
            )
            if has_location:
                _LOGGER.debug("Ignoring LBS location update for %s", self.kippy_id)
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
                _LOGGER.debug(
                    "Accepting LBS location update for %s "
                    "as current location is unknown",
                    self.kippy_id,
                )

        operating_status = data.get("operating_status")
        try:
            operating_status_int = int(operating_status)
        except (TypeError, ValueError):
            operating_status_int = None

        operating_status_str = OPERATING_STATUS_MAP.get(operating_status_int)
        if operating_status_int == OPERATING_STATUS.LIVE:
            self.update_interval = timedelta(seconds=self.live_refresh)
        else:
            self.update_interval = timedelta(seconds=self.idle_refresh)

        data["operating_status"] = operating_status_str
        return data

    def process_new_data(self, data: dict[str, Any]) -> None:
        """Process raw data and update the coordinator state."""
        self.async_set_updated_data(self._process_data(data))

    async def async_set_idle_refresh(self, value: int) -> None:
        """Update idle refresh value and interval when idle."""
        self.idle_refresh = value
        if self.data:
            operating_status = self.data.get("operating_status")
            if operating_status != OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]:
                self.update_interval = timedelta(seconds=self.idle_refresh)

    async def async_set_live_refresh(self, value: int) -> None:
        """Update live refresh value and interval when live."""
        self.live_refresh = value
        if self.data:
            operating_status = self.data.get("operating_status")
            if operating_status == OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]:
                self.update_interval = timedelta(seconds=self.live_refresh)


class KippyActivityCategoriesDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch activity category information."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: KippyApi,
        pet_ids: list[int],
    ) -> None:
        """Initialize the activity categories coordinator."""
        self.api = api
        self.config_entry = config_entry
        self.pet_ids = pet_ids
        kwargs: dict[str, Any] = {
            "name": f"{DOMAIN}_activities",
            "update_interval": None,
        }
        if _HAS_CONFIG_ENTRY:
            kwargs["config_entry"] = config_entry
        super().__init__(hass, _LOGGER, **kwargs)

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch activity categories for all configured pets."""
        now = dt_util.now()
        from_date = now.strftime("%Y-%m-%d")
        to_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        data: dict[int, dict[str, Any]] = {}
        try:
            for pet_id in self.pet_ids:
                data[pet_id] = await self.api.get_activity_categories(
                    pet_id, from_date, to_date, 2, 1
                )
        except (
            ClientError,
            AsyncioTimeoutError,
            RuntimeError,
            JSONDecodeError,
        ) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        return data

    async def async_refresh_pet(self, pet_id: int) -> None:
        """Manually refresh activity data for a single pet."""
        now = dt_util.now()
        from_date = now.strftime("%Y-%m-%d")
        to_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        result = await self.api.get_activity_categories(
            pet_id, from_date, to_date, 2, 1
        )
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


class ActivityRefreshTimer:
    """Schedule activity refreshes after the next contact time."""

    def __init__(
        self,
        hass: HomeAssistant,
        base_coordinator: KippyDataUpdateCoordinator,
        map_coordinator: KippyMapDataUpdateCoordinator,
        activity_coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet_id: int,
        delay_minutes: int = DEFAULT_ACTIVITY_REFRESH_DELAY,
    ) -> None:
        """Initialize the timer."""
        self.hass = hass
        self.base_coordinator = base_coordinator
        self.map_coordinator = map_coordinator
        self.activity_coordinator = activity_coordinator
        self.pet_id = pet_id
        self.delay_minutes = delay_minutes
        self._unsub_timer: Callable[[], None] | None = None
        self._unsub_base = base_coordinator.async_add_listener(self._schedule_refresh)
        self._unsub_map = map_coordinator.async_add_listener(self._schedule_refresh)
        self._schedule_refresh()

    def _get_update_frequency(self) -> int | None:
        for pet in self.base_coordinator.data.get("pets", []):
            if pet.get("petID") == self.pet_id:
                return pet.get("updateFrequency")
        return None

    def _schedule_refresh(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        contact = (
            self.map_coordinator.data.get("contact_time")
            if self.map_coordinator.data
            else None
        )
        update_frequency = self._get_update_frequency()
        if contact is None or update_frequency is None:
            return
        try:
            when = datetime.fromtimestamp(
                int(contact) + int(update_frequency) * 3600 + self.delay_minutes * 60,
                timezone.utc,
            )
        except (TypeError, ValueError, OSError):
            return
        now = dt_util.utcnow()
        if when <= now:
            when = now + timedelta(minutes=self.delay_minutes)
        self._unsub_timer = async_track_point_in_utc_time(
            self.hass, self._handle_refresh, when
        )

    async def _handle_refresh(self, _now) -> None:
        self._unsub_timer = None
        await self.activity_coordinator.async_refresh_pet(self.pet_id)
        await self.map_coordinator.async_request_refresh()

    async def async_set_delay(self, minutes: int) -> None:
        self.delay_minutes = minutes
        self._schedule_refresh()

    def async_cancel(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        if self._unsub_base:
            self._unsub_base()
            self._unsub_base = None
        if self._unsub_map:
            self._unsub_map()
            self._unsub_map = None
