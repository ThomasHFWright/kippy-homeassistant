"""Button entities for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .helpers import build_device_info
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KippyDataUpdateCoordinator, KippyMapDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy button entities."""
    coordinator: KippyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    map_coordinators: dict[int, KippyMapDataUpdateCoordinator] = hass.data[DOMAIN][
        entry.entry_id
    ]["map_coordinators"]
    entities: list[ButtonEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyPressButton(map_coordinators[pet["petID"]], pet))
    async_add_entities(entities)


class KippyPressButton(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], ButtonEntity
):
    """Button to trigger an immediate kippymap action."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Press" if pet_name else "Press"
        self._attr_unique_id = f"{self._pet_id}_press"
        self._pet_name = pet_name
        self._pet_data = pet
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_translation_key = "press"

    async def async_press(self) -> None:
        data = await self.coordinator.api.kippymap_action(self.coordinator.kippy_id)
        self.coordinator.async_set_updated_data(data)

    @property
    def device_info(self) -> DeviceInfo:
        name = f"Kippy {self._pet_name}" if self._pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)
