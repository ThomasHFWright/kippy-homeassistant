"""Sensor platform for Kippy."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import KippyDataUpdateCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Kippy sensors."""
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    coordinator = KippyDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([KippyExampleSensor(coordinator)])

class KippyExampleSensor(SensorEntity):
    """Representation of an example Kippy sensor."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Kippy Example"
        self._attr_unique_id = "kippy_example"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("example")
