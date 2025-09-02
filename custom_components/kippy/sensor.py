"""Sensor platform for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .helpers import build_device_info
from .const import DOMAIN, PET_KIND_TO_TYPE
from .coordinator import KippyDataUpdateCoordinator, KippyMapDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]
    entities: list[SensorEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyExpiredDaysSensor(coordinator, pet))
        entities.append(KippyPetTypeSensor(coordinator, pet))
        entities.append(KippyIDSensor(coordinator, pet))
        entities.append(KippyIMEISensor(coordinator, pet))
        map_coord = map_coordinators.get(pet["petID"])
        if map_coord:
            entities.append(KippyBatterySensor(map_coord, pet))
            entities.append(KippyLocalizationTechnologySensor(map_coord, pet))
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
        return build_device_info(self._pet_id, self._pet_data, name)


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


class KippyPetTypeSensor(_KippyBaseEntity, SensorEntity):
    """Sensor for pet type."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Type" if pet_name else "Pet Type"
        self._attr_unique_id = f"{self._pet_id}_type"

    @property
    def native_value(self) -> str | None:
        kind = self._pet_data.get("petKind")
        return PET_KIND_TO_TYPE.get(str(kind))


class KippyIDSensor(_KippyBaseEntity, SensorEntity):
    """Diagnostic sensor for the Kippy device ID."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Kippy ID" if pet_name else "Kippy ID"
        self._attr_unique_id = f"{self._pet_id}_kippy_id"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return self._pet_data.get("kippyID") or self._pet_data.get("kippy_id")


class KippyIMEISensor(_KippyBaseEntity, SensorEntity):
    """Diagnostic sensor for the device IMEI."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} IMEI" if pet_name else "IMEI"
        self._attr_unique_id = f"{self._pet_id}_imei"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return self._pet_data.get("kippyIMEI")


class KippyBatterySensor(CoordinatorEntity[KippyMapDataUpdateCoordinator], SensorEntity):
    """Sensor for device battery level."""

    def __init__(self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Battery Level" if pet_name else "Battery Level"
        self._attr_unique_id = f"{self._pet_id}_battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

    @property
    def native_value(self) -> Any:
        val = self.coordinator.data.get("battery") if self.coordinator.data else None
        if val is None:
            val = self._pet_data.get("battery") or self._pet_data.get("batteryLevel")
        try:
            return int(val)
        except (TypeError, ValueError):
            return None


class KippyLocalizationTechnologySensor(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], SensorEntity
):
    """Sensor for the technology used to determine location."""

    def __init__(self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Localization Technology"
            if pet_name
            else "Localization Technology"
        )
        self._attr_unique_id = f"{self._pet_id}_localization_technology"

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

    @property
    def native_value(self) -> Any:
        return (
            self.coordinator.data.get("localization_technology")
            if self.coordinator.data
            else None
        )

