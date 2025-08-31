"""The Kippy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .api import KippyApi
from .const import DOMAIN, PLATFORMS
from .coordinator import KippyDataUpdateCoordinator, KippyMapDataUpdateCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kippy from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    session = aiohttp_client.async_get_clientsession(hass)
    api = KippyApi(session)
    email = entry.data.get(CONF_EMAIL)
    password = entry.data.get(CONF_PASSWORD)
    if not email or not password:
        return False

    try:
        await api.login(email, password)
        coordinator = KippyDataUpdateCoordinator(hass, api)
        await coordinator.async_config_entry_first_refresh()

        map_coordinators = {}
        for pet in coordinator.data.get("pets", []):
            kippy_id = pet.get("kippyID") or pet.get("kippy_id") or pet.get("petID")
            map_coordinator = KippyMapDataUpdateCoordinator(hass, api, int(kippy_id))
            await map_coordinator.async_config_entry_first_refresh()
            map_coordinators[pet["petID"]] = map_coordinator
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "map_coordinators": map_coordinators,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Kippy config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["coordinator"].async_config_entry_last_unload()
        for coordinator in data["map_coordinators"].values():
            await coordinator.async_config_entry_last_unload()
    return unload_ok
