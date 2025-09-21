"""Button entities for Kippy pets."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    KippyActivityCategoriesDataUpdateCoordinator,
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)
from .helpers import build_device_info


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
    activity_coordinator: KippyActivityCategoriesDataUpdateCoordinator = hass.data[
        DOMAIN
    ][entry.entry_id]["activity_coordinator"]
    entities: list[ButtonEntity] = [KippyRefreshPetsButton(hass, entry)]
    for pet in coordinator.data.get("pets", []):
        map_coord = map_coordinators.get(pet["petID"])
        if not map_coord:
            continue
        entities.append(KippyRefreshMapAttributesButton(map_coord, pet))
        entities.append(KippyActivityCategoriesButton(activity_coordinator, pet))
    async_add_entities(entities)


class KippyRefreshMapAttributesButton(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], ButtonEntity
):
    """Button to refresh Kippy map attributes immediately."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Refresh Map Attributes"
            if pet_name
            else "Refresh Map Attributes"
        )
        self._attr_unique_id = f"{self._pet_id}_refresh_map_attributes"
        self._pet_name = pet_name
        self._pet_data = pet
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_translation_key = "refresh_map_attributes"

    async def async_press(self) -> None:
        data = await self.coordinator.api.kippymap_action(self.coordinator.kippy_id)
        self.coordinator.process_new_data(data)

    def press(self) -> None:
        raise NotImplementedError(
            "Synchronous button presses are not supported; use async_press instead."
        )

    @property
    def device_info(self) -> DeviceInfo:
        name = f"Kippy {self._pet_name}" if self._pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)


class KippyActivityCategoriesButton(ButtonEntity):
    """Button to manually refresh activity categories."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        self.coordinator = coordinator
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Refresh Activities" if pet_name else "Refresh Activities"
        )
        self._attr_unique_id = f"{self._pet_id}_refresh_activities"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_translation_key = "refresh_activities"

    async def async_press(self) -> None:
        await self.coordinator.async_refresh_pet(self._pet_id)

    def press(self) -> None:
        raise NotImplementedError(
            "Synchronous button presses are not supported; use async_press instead."
        )

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)


class KippyRefreshPetsButton(ButtonEntity):
    """Button to refresh the list of pets."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_name = "Refresh pets"
        self._attr_unique_id = f"{entry.entry_id}_refresh_pets"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_translation_key = "refresh_pets"
        self._reloading = False

    async def async_press(self) -> None:
        if self._reloading or self.entry.state is not ConfigEntryState.LOADED:
            raise HomeAssistantError("Entry is not loaded")
        self._reloading = True
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(self.entry.entry_id)
        )

    def press(self) -> None:
        raise NotImplementedError(
            "Synchronous button presses are not supported; use async_press instead."
        )
