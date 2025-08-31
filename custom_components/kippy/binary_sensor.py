"""Binary sensors for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPERATING_STATUS_LIVE
from .coordinator import KippyDataUpdateCoordinator, KippyMapDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]
    entities: list[BinarySensorEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyFirmwareUpgradeAvailableBinarySensor(coordinator, pet))
        entities.append(KippyLiveTrackingBinarySensor(map_coordinators[pet["petID"]], pet))
    async_add_entities(entities)


class KippyFirmwareUpgradeAvailableBinarySensor(
    CoordinatorEntity[KippyDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor indicating firmware upgrade availability."""

    def __init__(self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Firmware Upgrade available" if pet_name else "Firmware Upgrade available"
        )
        self._attr_unique_id = f"{self._pet_id}_firmware_upgrade"
        self._pet_data = pet
        self._attr_translation_key = "firmware_upgrade_available"

    @property
    def is_on(self) -> bool:
        return bool(self._pet_data.get("firmware_need_upgrade"))

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


class KippyLiveTrackingBinarySensor(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor indicating live tracking status."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Live tracking" if pet_name else "Live tracking"
        )
        self._attr_unique_id = f"{self._pet_id}_live_tracking"
        self._pet_name = pet_name
        self._attr_translation_key = "live_tracking"

    @property
    def is_on(self) -> bool:
        return bool(
            self.coordinator.data.get("operating_status") == OPERATING_STATUS_LIVE
        )

    @property
    def device_info(self) -> DeviceInfo:
        name = f"Kippy {self._pet_name}" if self._pet_name else "Kippy"
        return DeviceInfo(
            identifiers={(DOMAIN, self._pet_id)},
            name=name,
            manufacturer="Kippy",
        )

