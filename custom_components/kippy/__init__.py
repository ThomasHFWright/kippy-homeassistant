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
    KippyActivityCategoriesDataUpdateCoordinator,
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kippy from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    session = aiohttp_client.async_get_clientsession(hass)
    api = await KippyApi.async_create(session)
    email = entry.data.get(CONF_EMAIL)
    password = entry.data.get(CONF_PASSWORD)
    if not email or not password:
        return False

    try:
        await api.login(email, password)
        coordinator = KippyDataUpdateCoordinator(hass, entry, api)
        await coordinator.async_config_entry_first_refresh()

        map_coordinators = {}
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
            map_coordinators[pet["petID"]] = map_coordinator
            pet_ids.append(pet["petID"])

        activity_coordinator = KippyActivityCategoriesDataUpdateCoordinator(
            hass, entry, api, pet_ids
        )
        await activity_coordinator.async_config_entry_first_refresh()
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
