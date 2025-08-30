"""The Kippy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import KippyApi
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kippy from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    session = aiohttp_client.async_get_clientsession(hass)
    api = KippyApi(session)
    await api.login(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    hass.data[DOMAIN][entry.entry_id] = {"api": api}
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Kippy config entry."""
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
