"""Number entities for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .helpers import build_device_info
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOCALIZATION_TECHNOLOGY_GPS
from .coordinator import KippyDataUpdateCoordinator, KippyMapDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy number entities."""
    base_coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]
    entities: list[NumberEntity] = []
    for pet in base_coordinator.data.get("pets", []):
        expired_days = pet.get("expired_days")
        is_expired = False
        try:
            is_expired = int(expired_days) >= 0
        except (TypeError, ValueError):
            pass

        if not is_expired:
            entities.append(KippyUpdateFrequencyNumber(base_coordinator, pet))

        map_coord = map_coordinators.get(pet["petID"])
        if not map_coord:
            continue
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
            f"{pet_name} {LOCALIZATION_TECHNOLOGY_GPS} Automatic update frequency (hours)"
            if pet_name
            else f"{LOCALIZATION_TECHNOLOGY_GPS} Automatic update frequency (hours)"
        )
        self._attr_unique_id = f"{self._pet_id}_update_frequency"
        self._pet_data = pet

    @property
    def native_value(self) -> float | None:
        value = self._pet_data.get("updateFrequency")
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        kippy_id = self._pet_data.get("kippyID") or self._pet_data.get("kippy_id")
        gps_val = self._pet_data.get("gpsOnDefault")
        if gps_val is None:
            gps_val = self._pet_data.get("gps_on_default")
        try:
            gps_on_default = bool(int(gps_val))
        except (TypeError, ValueError):
            gps_on_default = bool(gps_val)

        if kippy_id is not None:
            data = await self.coordinator.api.modify_kippy_settings(
                int(kippy_id), update_frequency=value, gps_on_default=gps_on_default
            )
            new_value = data.get("update_frequency", value)
            self._pet_data["updateFrequency"] = int(new_value)
        else:
            self._pet_data["updateFrequency"] = int(value)
        self.async_write_ha_state()
        self.coordinator.async_update_listeners()

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
    _attr_entity_category = EntityCategory.CONFIG

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
    _attr_entity_category = EntityCategory.CONFIG

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

