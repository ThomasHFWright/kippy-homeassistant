"""Sensor platform for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KippyDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyExpiredDaysSensor(coordinator, pet))
        entities.append(KippyPetKindSensor(coordinator, pet))
    async_add_entities(entities)


class _KippyBaseEntity(CoordinatorEntity[KippyDataUpdateCoordinator]):
    """Base entity for Kippy sensors."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet

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


class KippyExpiredDaysSensor(_KippyBaseEntity, SensorEntity):
    """Sensor for remaining service days."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Days Until Expiry" if pet_name else "Days Until Expiry"
        )
        self._attr_unique_id = f"{self._pet_id}_expired_days"

    @property
    def native_value(self) -> Any:
        days = self._pet_data.get("expired_days")
        if days is None:
            return None
        try:
            days = int(days)
        except (TypeError, ValueError):
            return None
        return abs(days) if days < 0 else "Expired"


class KippyPetKindSensor(_KippyBaseEntity, SensorEntity):
    """Sensor for pet type."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Kind" if pet_name else "Pet Kind"
        self._attr_unique_id = f"{self._pet_id}_kind"

    @property
    def native_value(self) -> str | None:
        kind = self._pet_data.get("petKind")
        if kind == 4:
            return "dog"
        if kind == 3:
            return "cat"
        return None

