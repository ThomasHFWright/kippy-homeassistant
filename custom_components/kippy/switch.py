"""Switch entities for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPERATING_STATUS_LIVE
from .coordinator import (
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]
    entities: list[SwitchEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyEnergySavingSwitch(coordinator, pet))
        entities.append(KippyLiveTrackingSwitch(map_coordinators[pet["petID"]], pet))
    async_add_entities(entities)


class KippyEnergySavingSwitch(
    CoordinatorEntity[KippyDataUpdateCoordinator], SwitchEntity
):
    """Switch for energy saving mode."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Energy Saving" if pet_name else "Energy Saving"
        )
        self._attr_unique_id = f"{self._pet_id}_energy_saving"
        self._pet_data = pet

    @property
    def is_on(self) -> bool:
        return bool(int(self._pet_data.get("energySavingMode", 0)))

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._pet_data["energySavingMode"] = 1
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._pet_data["energySavingMode"] = 0
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


class KippyLiveTrackingSwitch(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], SwitchEntity
):
    """Switch to toggle live tracking."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Toggle live tracking" if pet_name else "Toggle live tracking"
        )
        self._attr_unique_id = f"{self._pet_id}_toggle_live_tracking"
        self._pet_name = pet_name
        self._attr_translation_key = "toggle_live_tracking"

    @property
    def is_on(self) -> bool:
        return bool(
            self.coordinator.data.get("operating_status") == OPERATING_STATUS_LIVE
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        data = await self.coordinator.api.kippymap_action(
            self._pet_id, app_action=1
        )
        self.coordinator.async_set_updated_data(data)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        data = await self.coordinator.api.kippymap_action(
            self._pet_id, app_action=1
        )
        self.coordinator.async_set_updated_data(data)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        name = f"Kippy {self._pet_name}" if self._pet_name else "Kippy"
        return DeviceInfo(
            identifiers={(DOMAIN, self._pet_id)},
            name=name,
            manufacturer="Kippy",
        )

