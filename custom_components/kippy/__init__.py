"""The Kippy integration."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable

from aiohttp import ClientResponseError
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .api import KippyApi
from .const import DOMAIN, PLATFORMS
from .coordinator import (
    ActivityRefreshContext,
    ActivityRefreshTimer,
    CoordinatorContext,
    KippyActivityCategoriesDataUpdateCoordinator,
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)
from .helpers import (
    API_EXCEPTIONS,
    get_device_update_interval_minutes,
    get_map_refresh_settings,
    is_pet_subscription_active,
    normalize_kippy_identifier,
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

        async def _async_reload_entry() -> None:
            if entry.state is not ConfigEntryState.LOADED:
                return
            await hass.config_entries.async_reload(entry.entry_id)

        coordinator = KippyDataUpdateCoordinator(
            hass, entry, api, on_new_pets=_async_reload_entry
        )
        await coordinator.async_config_entry_first_refresh()

        context = CoordinatorContext(hass, entry, api)
        map_coordinators, pet_ids = await _async_build_map_coordinators(
            context, coordinator
        )
        activity_coordinator = KippyActivityCategoriesDataUpdateCoordinator(
            context, pet_ids
        )
        await activity_coordinator.async_config_entry_first_refresh()

        activity_timers = _build_activity_timers(
            hass, coordinator, map_coordinators, activity_coordinator
        )
    except API_EXCEPTIONS as err:
        if isinstance(err, ClientResponseError) and getattr(err, "status", None) in (
            401,
            403,
        ):
            raise ConfigEntryAuthFailed from err
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "map_coordinators": map_coordinators,
        "activity_coordinator": activity_coordinator,
        "activity_timers": activity_timers,
    }

    async def _async_options_updated(
        hass: HomeAssistant, updated_entry: ConfigEntry
    ) -> None:
        data = hass.data.get(DOMAIN, {}).get(updated_entry.entry_id)
        if not data:
            return
        base_coordinator: KippyDataUpdateCoordinator = data["coordinator"]
        base_coordinator.set_update_interval_minutes(
            get_device_update_interval_minutes(updated_entry)
        )

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Kippy config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data is not None:
            for timer in data.get("activity_timers", {}).values():
                timer.async_cancel()
            shutdown_tasks: list[Awaitable[Any]] = []

            def _collect_shutdown(target: Any) -> None:
                shutdown = getattr(target, "async_shutdown", None)
                if shutdown is not None:
                    shutdown_tasks.append(shutdown())

            coordinator = data.get("coordinator")
            if coordinator is not None:
                _collect_shutdown(coordinator)

            for map_coordinator in data.get("map_coordinators", {}).values():
                _collect_shutdown(map_coordinator)

            activity_coordinator = data.get("activity_coordinator")
            if activity_coordinator is not None:
                _collect_shutdown(activity_coordinator)

            if shutdown_tasks:
                await asyncio.gather(*shutdown_tasks)
    return unload_ok


async def _async_build_map_coordinators(
    context: CoordinatorContext,
    coordinator: KippyDataUpdateCoordinator,
) -> tuple[dict[int | str, KippyMapDataUpdateCoordinator], list[int | str]]:
    """Create map coordinators for pets with active subscriptions."""

    map_coordinators: dict[int | str, KippyMapDataUpdateCoordinator] = {}
    active_pet_ids: list[int | str] = []
    for pet in coordinator.data.get("pets", []):
        if not is_pet_subscription_active(pet):
            continue
        pet_id = pet.get("petID")
        if pet_id is None:
            continue
        kippy_id = normalize_kippy_identifier(pet, include_pet_id=True)
        if kippy_id is None:
            continue
        settings = get_map_refresh_settings(context.config_entry, pet_id)
        map_coordinator = KippyMapDataUpdateCoordinator(
            context, kippy_id, settings=settings
        )
        await map_coordinator.async_config_entry_first_refresh()
        map_coordinators[pet_id] = map_coordinator
        active_pet_ids.append(pet_id)
    return map_coordinators, active_pet_ids


def _build_activity_timers(
    hass: HomeAssistant,
    coordinator: KippyDataUpdateCoordinator,
    map_coordinators: dict[int | str, KippyMapDataUpdateCoordinator],
    activity_coordinator: KippyActivityCategoriesDataUpdateCoordinator,
) -> dict[int | str, ActivityRefreshTimer]:
    """Create timers that refresh activities after contact."""

    timers: dict[int | str, ActivityRefreshTimer] = {}
    for pet_id, map_coordinator in map_coordinators.items():
        context = ActivityRefreshContext(
            hass=hass,
            base=coordinator,
            map=map_coordinator,
            activity=activity_coordinator,
        )
        timers[pet_id] = ActivityRefreshTimer(context, pet_id)
    return timers
