"""Number entities for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .helpers import build_device_info
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KippyDataUpdateCoordinator, KippyMapDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy number entities."""
    base_coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]
    entities: list[NumberEntity] = []
    for pet in base_coordinator.data.get("pets", []):
        entities.append(KippyUpdateFrequencyNumber(base_coordinator, pet))
        map_coord = map_coordinators[pet["petID"]]
        entities.append(KippyIdleUpdateFrequencyNumber(map_coord, pet))
        entities.append(KippyLiveUpdateFrequencyNumber(map_coord, pet))
    async_add_entities(entities)


class KippyUpdateFrequencyNumber(CoordinatorEntity[KippyDataUpdateCoordinator], NumberEntity):
    """Number entity for GPS automatic update frequency."""

    _attr_native_min_value = 1
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "h"

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} GPS Automatic update frequency (hours)"
            if pet_name
            else "GPS Automatic update frequency (hours)"
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
        return build_device_info(self._pet_id, self._pet_data, name)


class KippyIdleUpdateFrequencyNumber(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], NumberEntity
):
    """Number entity for idle update frequency."""

    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Idle update frequency (minutes)"
            if pet_name
            else "Idle update frequency (minutes)"
        )
        self._attr_unique_id = f"{self._pet_id}_idle_refresh_time"

    @property
    def native_value(self) -> float | None:
        return float(self.coordinator.idle_refresh) / 60

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_idle_refresh(int(value * 60))
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)


class KippyLiveUpdateFrequencyNumber(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], NumberEntity
):
    """Number entity for live update frequency."""

    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "s"

    def __init__(self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Live update frequency (seconds)"
            if pet_name
            else "Live update frequency (seconds)"
        )
        self._attr_unique_id = f"{self._pet_id}_live_refresh_time"

    @property
    def native_value(self) -> float | None:
        return float(self.coordinator.live_refresh)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_live_refresh(int(value))
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

