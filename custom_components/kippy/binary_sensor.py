"""Binary sensors for Kippy pets."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KippyDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[BinarySensorEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyFirmwareUpgradeAvailableBinarySensor(coordinator, pet))
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

