"""The Kippy integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
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
        coordinator = KippyDataUpdateCoordinator(hass, entry, api)
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
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "map_coordinators": map_coordinators,
        "activity_coordinator": activity_coordinator,
        "activity_timers": activity_timers,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Kippy config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data[DOMAIN].pop(entry.entry_id)
    for timer in data.get("activity_timers", {}).values():
        timer.async_cancel()
    return True


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
        map_coordinator = KippyMapDataUpdateCoordinator(context, kippy_id)
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
