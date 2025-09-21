"""Shared base entities for the Kippy integration."""

from __future__ import annotations

from typing import Any, Sequence

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import KippyDataUpdateCoordinator, KippyMapDataUpdateCoordinator
from .helpers import build_device_info, update_pet_data


class KippyPetEntity(CoordinatorEntity[KippyDataUpdateCoordinator]):
    """Base entity for pet-specific coordinator data."""

    _preserve_fields: Sequence[str] = ()

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet

    def _handle_coordinator_update(self) -> None:
        self._pet_data = update_pet_data(
            self.coordinator.data.get("pets", []),
            self._pet_id,
            self._pet_data,
            self._preserve_fields,
        )
        super()._handle_coordinator_update()

    @property
    def device_info(self) -> DeviceInfo:
        return build_device_info(self._pet_id, self._pet_data)


class KippyMapEntity(CoordinatorEntity[KippyMapDataUpdateCoordinator]):
    """Base entity for map coordinator data."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet

    @property
    def device_info(self) -> DeviceInfo:
        return build_device_info(self._pet_id, self._pet_data)
