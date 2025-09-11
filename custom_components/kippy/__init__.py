"""The Kippy integration."""
from __future__ import annotations

from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .api import KippyApi
from .const import (
    DOMAIN,
    PLATFORMS,
)
from .coordinator import (
    KippyActivityCategoriesDataUpdateCoordinator,
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kippy from a config entry."""
    email = entry.data.get(CONF_EMAIL)
    password = entry.data.get(CONF_PASSWORD)
    if not email or not password:
        return False

    hass.data.setdefault(DOMAIN, {})
    session = aiohttp_client.async_get_clientsession(hass)
    api = await KippyApi.async_create(session)

    try:
        await api.login(email, password)
        coordinator = KippyDataUpdateCoordinator(hass, entry, api)
        await coordinator.async_config_entry_first_refresh()

        map_coordinators: dict[int, KippyMapDataUpdateCoordinator] = {}
        pet_ids: list[int] = []
        for pet in coordinator.data.get("pets", []):
            expired_days = pet.get("expired_days")
            try:
                if int(expired_days) >= 0:
                    continue
            except (TypeError, ValueError):
                pass

            kippy_id = pet.get("kippyID") or pet.get("kippy_id") or pet.get("petID")
            map_coordinator = KippyMapDataUpdateCoordinator(
                hass, entry, api, int(kippy_id)
            )
            await map_coordinator.async_config_entry_first_refresh()
            pet_id = int(pet["petID"])
            map_coordinators[pet_id] = map_coordinator
            pet_ids.append(pet_id)

        activity_coordinator = KippyActivityCategoriesDataUpdateCoordinator(
            hass, entry, api, pet_ids
        )
        await activity_coordinator.async_config_entry_first_refresh()

        def _create_scheduler(pet_id: int, map_coord: KippyMapDataUpdateCoordinator) -> None:
            cancel_cb: Callable[[], None] | None = None

            def schedule() -> None:
                nonlocal cancel_cb
                if cancel_cb:
                    cancel_cb()
                    cancel_cb = None
                contact = map_coord.data.get("contact_time") if map_coord.data else None
                pet_data = next(
                    (
                        p
                        for p in coordinator.data.get("pets", [])
                        if int(p.get("petID")) == pet_id
                    ),
                    {},
                )
                update_freq = pet_data.get("updateFrequency")
                if contact is None or update_freq is None:
                    return
                try:
                    next_ts = int(contact) + int(update_freq) * 3600 + map_coord.activity_refresh_delay
                except (TypeError, ValueError):
                    return
                delay = max(0, next_ts - dt_util.utcnow().timestamp())

                def _run(now):
                    hass.async_create_task(activity_coordinator.async_refresh_pet(pet_id))
                    hass.async_create_task(map_coord.async_request_refresh())

                cancel_cb = async_call_later(hass, delay, _run)

            map_coord.set_activity_refresh_scheduler(schedule)
            map_coord.async_add_listener(schedule)
            coordinator.async_add_listener(schedule)
            entry.async_on_unload(lambda: cancel_cb() if cancel_cb else None)
            schedule()

        for pet_id, map_coord in map_coordinators.items():
            _create_scheduler(pet_id, map_coord)
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "map_coordinators": map_coordinators,
        "activity_coordinator": activity_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Kippy config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
