"""Device tracker platform for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import TrackerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PET_KIND_TO_TYPE
from .coordinator import KippyMapDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Kippy device trackers."""
    base_coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]

    entities = [
        KippyPetTracker(map_coordinators[pet["petID"]], pet)
        for pet in base_coordinator.data.get("pets", [])
    ]
    async_add_entities(entities)


class KippyPetTracker(CoordinatorEntity[KippyMapDataUpdateCoordinator], TrackerEntity):
    """Representation of a Kippy tracked pet."""

    def __init__(self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        """Initialize the tracker entity."""
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = f"Kippy {pet_name}" if pet_name else "Kippy"
        self._attr_unique_id = pet["petID"]
        self._pet_data = dict(pet)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the attributes provided by the API."""
        attrs = dict(self._pet_data)
        attrs.update(self.coordinator.data or {})
        expired_days = attrs.get("expired_days")
        if isinstance(expired_days, (int, str)):
            try:
                expired_days = int(expired_days)
                attrs["expired_days"] = (
                    abs(expired_days) if expired_days < 0 else "Expired"
                )
            except ValueError:
                pass

        pet_kind = attrs.pop("petKind", None)
        pet_type = PET_KIND_TO_TYPE.get(str(pet_kind))
        if pet_type:
            attrs["petType"] = pet_type

        return attrs

    @property
    def source_type(self) -> SourceType:
        """GPS will be provided in a separate update flow later."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude if available."""
        lat = self.coordinator.data.get("gps_latitude") if self.coordinator.data else None
        return float(lat) if lat is not None else None

    @property
    def longitude(self) -> float | None:
        """Return longitude if available."""
        lon = self.coordinator.data.get("gps_longitude") if self.coordinator.data else None
        return float(lon) if lon is not None else None

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

    def _handle_coordinator_update(self) -> None:  # pragma: no cover - simple passthrough
        super()._handle_coordinator_update()
