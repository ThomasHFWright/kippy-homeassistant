"""Number entities for Kippy pets."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, LOCALIZATION_TECHNOLOGY_GPS
from .coordinator import (
    ActivityRefreshTimer,
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)
from .entity import KippyMapEntity, KippyPetEntity
from .helpers import (
    build_device_info,
    is_pet_subscription_active,
    normalize_kippy_identifier,
)

SYNC_VALUE_ERROR = "Synchronous updates are not supported; use async_set_native_value."


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy number entities."""
    base_coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]
    activity_timers = hass.data[DOMAIN][entry.entry_id]["activity_timers"]
    entities: list[NumberEntity] = []
    for pet in base_coordinator.data.get("pets", []):
        if is_pet_subscription_active(pet):
            entities.append(KippyUpdateFrequencyNumber(base_coordinator, pet))

        map_coord = map_coordinators.get(pet["petID"])
        if not map_coord:
            continue
        entities.append(KippyIdleUpdateFrequencyNumber(map_coord, pet))
        entities.append(KippyLiveUpdateFrequencyNumber(map_coord, pet))
        timer = activity_timers.get(pet["petID"])
        if timer:
            entities.append(KippyActivityRefreshDelayNumber(timer, pet))
    async_add_entities(entities)


class KippyUpdateFrequencyNumber(KippyPetEntity, NumberEntity):
    """Number entity for GPS automatic update frequency."""

    _attr_native_min_value = 1
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "h"

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} {LOCALIZATION_TECHNOLOGY_GPS} "
            "Automatic update frequency (hours)"
            if pet_name
            else f"{LOCALIZATION_TECHNOLOGY_GPS} Automatic update frequency (hours)"
        )
        self._attr_unique_id = f"{self._pet_id}_update_frequency"
        self._attr_translation_key = "update_frequency"

    @property
    def native_value(self) -> float | None:
        value = self._pet_data.get("updateFrequency")
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        kippy_id = normalize_kippy_identifier(self._pet_data)
        gps_val = self._pet_data.get("gpsOnDefault")
        if gps_val is None:
            gps_val = self._pet_data.get("gps_on_default")
        try:
            gps_on_default = bool(int(gps_val))
        except (TypeError, ValueError):
            gps_on_default = bool(gps_val)

        if kippy_id is not None:
            data = await self.coordinator.api.modify_kippy_settings(
                kippy_id, update_frequency=value, gps_on_default=gps_on_default
            )
            new_value = data.get("update_frequency", value)
            self._pet_data["updateFrequency"] = int(new_value)
        else:
            self._pet_data["updateFrequency"] = int(value)
        self.async_write_ha_state()
        self.coordinator.async_update_listeners()

    def set_native_value(self, value: float) -> None:
        raise NotImplementedError(SYNC_VALUE_ERROR)


class KippyIdleUpdateFrequencyNumber(KippyMapEntity, NumberEntity):
    """Number entity for idle update frequency."""

    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Idle update frequency (minutes)"
            if pet_name
            else "Idle update frequency (minutes)"
        )
        self._attr_unique_id = f"{self._pet_id}_idle_refresh_time"
        self._attr_translation_key = "idle_refresh_time"

    @property
    def native_value(self) -> float | None:
        return float(self.coordinator.idle_refresh) / 60

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_idle_refresh(int(value * 60))
        self.async_write_ha_state()

    def set_native_value(self, value: float) -> None:
        raise NotImplementedError(SYNC_VALUE_ERROR)


class KippyLiveUpdateFrequencyNumber(KippyMapEntity, NumberEntity):
    """Number entity for live update frequency."""

    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "s"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Live update frequency (seconds)"
            if pet_name
            else "Live update frequency (seconds)"
        )
        self._attr_unique_id = f"{self._pet_id}_live_refresh_time"
        self._attr_translation_key = "live_refresh_time"

    @property
    def native_value(self) -> float | None:
        return float(self.coordinator.live_refresh)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_live_refresh(int(value))
        self.async_write_ha_state()

    def set_native_value(self, value: float) -> None:
        raise NotImplementedError(SYNC_VALUE_ERROR)

class KippyActivityRefreshDelayNumber(NumberEntity):
    """Number to control activity refresh delay."""

    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, timer: ActivityRefreshTimer, pet: dict[str, Any]) -> None:
        self.timer = timer
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Activity refresh delay (minutes)"
            if pet_name
            else "Activity refresh delay (minutes)"
        )
        self._attr_unique_id = f"{self._pet_id}_activity_refresh_delay"

    @property
    def native_value(self) -> float | None:
        return float(self.timer.delay_minutes)

    async def async_set_native_value(self, value: float) -> None:
        await self.timer.async_set_delay(int(value))
        self.async_write_ha_state()

    def set_native_value(self, value: float) -> None:
        raise NotImplementedError(SYNC_VALUE_ERROR)

    @property
    def device_info(self) -> DeviceInfo:
        return build_device_info(self._pet_id, self._pet_data)
