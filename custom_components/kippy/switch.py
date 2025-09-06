"""Switch entities for Kippy pets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .helpers import build_device_info
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    LOCALIZATION_TECHNOLOGY_LBS,
    OPERATING_STATUS,
    OPERATING_STATUS_MAP,
)
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
        map_coord = map_coordinators[pet["petID"]]
        entities.append(KippyEnergySavingSwitch(coordinator, pet, map_coord))
        entities.append(KippyLiveTrackingSwitch(map_coord, pet))
        entities.append(KippyIgnoreLBSSwitch(map_coord, pet))
    async_add_entities(entities)


class KippyEnergySavingSwitch(
    CoordinatorEntity[KippyDataUpdateCoordinator], SwitchEntity
):
    """Switch for energy saving mode."""

    def __init__(
        self,
        coordinator: KippyDataUpdateCoordinator,
        pet: dict[str, Any],
        map_coordinator: KippyMapDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Energy Saving" if pet_name else "Energy Saving"
        )
        self._attr_unique_id = f"{self._pet_id}_energy_saving"
        self._pet_data = pet
        self._map_coordinator = map_coordinator
        self.async_on_remove(
            map_coordinator.async_add_listener(self._handle_map_update)
        )

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

    def _handle_map_update(self) -> None:
        if (
            self._map_coordinator.data
            and self._map_coordinator.data.get("operating_status")
            == OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
        ):
            if int(self._pet_data.get("energySavingMode", 0)) != 1:
                self._pet_data["energySavingMode"] = 1
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)


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
        self._pet_data = pet
        self._attr_translation_key = "toggle_live_tracking"

    @property
    def is_on(self) -> bool:
        return bool(
            self.coordinator.data.get("operating_status")
            == OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        data = await self.coordinator.api.kippymap_action(
            self.coordinator.kippy_id, app_action=1
        )
        self.coordinator.async_set_updated_data(data)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        data = await self.coordinator.api.kippymap_action(
            self.coordinator.kippy_id, app_action=1
        )
        self.coordinator.async_set_updated_data(data)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        name = f"Kippy {self._pet_name}" if self._pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)


class KippyIgnoreLBSSwitch(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], SwitchEntity
):
    """Switch to ignore low accuracy LBS location updates."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_name = pet.get("petName")
        self._pet_data = pet
        self._attr_name = (
            f"{self._pet_name} Ignore {LOCALIZATION_TECHNOLOGY_LBS} updates"
            if self._pet_name
            else f"Ignore {LOCALIZATION_TECHNOLOGY_LBS} updates"
        )
        self._attr_unique_id = f"{self._pet_id}_ignore_lbs"
        self._attr_translation_key = "ignore_lbs_updates"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        return self.coordinator.ignore_lbs

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.ignore_lbs = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.ignore_lbs = False
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        name = f"Kippy {self._pet_name}" if self._pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

