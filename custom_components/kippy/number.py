"""Number entities for Kippy pets."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KippyDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[NumberEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyUpdateFrequencyNumber(coordinator, pet))
    async_add_entities(entities)


class KippyUpdateFrequencyNumber(CoordinatorEntity[KippyDataUpdateCoordinator], NumberEntity):
    """Number entity for update frequency."""

    _attr_native_min_value = 1
    _attr_native_max_value = 24
    _attr_native_step = 1

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Update Frequency" if pet_name else "Update Frequency"
        )
        self._attr_unique_id = f"{self._pet_id}_update_frequency"
        self._pet_data = pet

    @property
    def native_value(self) -> float | None:
        value = self._pet_data.get("updateFrequency")
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        self._pet_data["updateFrequency"] = int(value)
        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        for pet in self.coordinator.data.get("pets", []):
            if pet.get("petID") == self._pet_id:
                self._pet_data = pet
                break
        super()._handle_coordinator_update()

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return DeviceInfo(
            identifiers={(DOMAIN, self._pet_id)},
            name=name,
            manufacturer="Kippy",
            model=self._pet_data.get("kippyType"),
            sw_version=self._pet_data.get("kippyFirmware"),
        )

