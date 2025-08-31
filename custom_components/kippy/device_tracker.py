"""Device tracker platform for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import TrackerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KippyDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Kippy device trackers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        KippyPetTracker(coordinator, pet)
        for pet in coordinator.data.get("pets", [])
    ]
    async_add_entities(entities)


class KippyPetTracker(CoordinatorEntity[KippyDataUpdateCoordinator], TrackerEntity):
    """Representation of a Kippy tracked pet."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        """Initialize the tracker entity."""
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._attr_name = pet.get("petName")
        self._attr_unique_id = pet["petID"]
        self._pet_data = pet

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the attributes provided by the API."""
        return self._pet_data

    @property
    def source_type(self) -> SourceType:
        """GPS will be provided in a separate update flow later."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude if available."""
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude if available."""
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this pet."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._pet_id)},
            name=self._attr_name,
            manufacturer="Kippy",
            model=self._pet_data.get("kippyType"),
            sw_version=self._pet_data.get("kippyFirmware"),
        )

    def _handle_coordinator_update(self) -> None:
        """Update internal data from the coordinator."""
        for pet in self.coordinator.data.get("pets", []):
            if pet.get("petID") == self._pet_id:
                self._pet_data = pet
                break
        super()._handle_coordinator_update()
