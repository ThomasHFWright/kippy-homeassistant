"""Switch entities for Kippy pets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    APP_ACTION,
    DOMAIN,
    LOCALIZATION_TECHNOLOGY_LBS,
    OPERATING_STATUS,
    OPERATING_STATUS_MAP,
)
from .coordinator import (
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)
from .helpers import build_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]
    entities: list[SwitchEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyGpsDefaultSwitch(coordinator, pet))
        map_coord = map_coordinators.get(pet["petID"])
        if not map_coord:
            continue
        entities.append(KippyEnergySavingSwitch(coordinator, pet, map_coord))
        entities.append(KippyLiveTrackingSwitch(map_coord, pet))
        entities.append(KippyIgnoreLBSSwitch(map_coord, pet))
    async_add_entities(entities)


class KippyGpsDefaultSwitch(
    CoordinatorEntity[KippyDataUpdateCoordinator], SwitchEntity
):
    """Switch to enable or disable GPS tracking by default."""

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} GPS tracking" if pet_name else "GPS tracking"
        self._attr_unique_id = f"{self._pet_id}_gps_on_default"
        self._pet_data = pet
        self._attr_translation_key = "gps_on_default"

    @property
    def is_on(self) -> bool:
        value = self._pet_data.get("gpsOnDefault")
        if value is None:
            value = self._pet_data.get("gps_on_default")
        try:
            return bool(int(value))
        except (TypeError, ValueError):
            return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        kippy_id = self._pet_data.get("kippyID") or self._pet_data.get("kippy_id")
        if kippy_id is not None:
            await self.coordinator.api.modify_kippy_settings(
                int(kippy_id), gps_on_default=True
            )
        self._pet_data["gpsOnDefault"] = 1
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        kippy_id = self._pet_data.get("kippyID") or self._pet_data.get("kippy_id")
        if kippy_id is not None:
            await self.coordinator.api.modify_kippy_settings(
                int(kippy_id), gps_on_default=False
            )
        self._pet_data["gpsOnDefault"] = 0
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
        return build_device_info(self._pet_id, self._pet_data, name)


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
        self._attr_name = f"{pet_name} Energy Saving" if pet_name else "Energy Saving"
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
        kippy_id = self._pet_data.get("kippyID") or self._pet_data.get("kippy_id")
        if kippy_id is not None:
            await self.coordinator.api.modify_kippy_settings(
                int(kippy_id), energy_saving_mode=True
            )
        self._pet_data["energySavingMode"] = 1
        self.async_write_ha_state()
        await self._async_notify_next_call_time()

    async def async_turn_off(self, **kwargs: Any) -> None:
        kippy_id = self._pet_data.get("kippyID") or self._pet_data.get("kippy_id")
        if kippy_id is not None:
            await self.coordinator.api.modify_kippy_settings(
                int(kippy_id), energy_saving_mode=False
            )
        self._pet_data["energySavingMode"] = 0
        self.async_write_ha_state()
        await self._async_notify_next_call_time()

    async def _async_notify_next_call_time(self) -> None:
        """Notify user that change will apply at next call time."""
        await self._map_coordinator.async_request_refresh()
        if not self._map_coordinator.data:
            return
        ts = self._map_coordinator.data.get("next_call_time")
        try:
            next_call = datetime.fromtimestamp(int(ts), timezone.utc)
        except (TypeError, ValueError, OSError):
            return
        now = dt_util.utcnow()
        hours = max(int((next_call - now).total_seconds() // 3600), 0)
        local_time = dt_util.as_local(next_call)
        message = f"This change will apply in {hours} hours at {local_time.isoformat()}"
        await self.hass.services.async_call(
            persistent_notification.DOMAIN,
            "create",
            {
                persistent_notification.ATTR_MESSAGE: message,
                persistent_notification.ATTR_TITLE: self.name,
            },
        )

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
    """Switch for live tracking."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Live tracking" if pet_name else "Live tracking"
        self._attr_unique_id = f"{self._pet_id}_live_tracking"
        self._pet_name = pet_name
        self._pet_data = pet
        self._attr_translation_key = "live_tracking"

    @property
    def is_on(self) -> bool:
        return bool(
            self.coordinator.data.get("operating_status")
            == OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]
        )

    @property
    def available(self) -> bool:
        return (
            self.coordinator.data.get("operating_status")
            != OPERATING_STATUS_MAP[OPERATING_STATUS.ENERGY_SAVING]
            and super().available
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.available:
            self.async_write_ha_state()
            raise HomeAssistantError(
                "Live tracking cannot be enabled in energy saving mode"
            )
        data = await self.coordinator.api.kippymap_action(
            self.coordinator.kippy_id,
            app_action=APP_ACTION.TURN_LIVE_TRACKING_ON,
        )
        self.coordinator.process_new_data(data)
        if (
            self.coordinator.data.get("operating_status")
            == OPERATING_STATUS_MAP[OPERATING_STATUS.IDLE]
        ):
            self.coordinator.data["operating_status"] = OPERATING_STATUS_MAP[
                OPERATING_STATUS.LIVE
            ]
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if not self.available:
            self.async_write_ha_state()
            raise HomeAssistantError(
                "Live tracking cannot be disabled in energy saving mode"
            )
        data = await self.coordinator.api.kippymap_action(
            self.coordinator.kippy_id,
            app_action=APP_ACTION.TURN_LIVE_TRACKING_OFF,
        )
        self.coordinator.process_new_data(data)
        if (
            self.coordinator.data.get("operating_status")
            == OPERATING_STATUS_MAP[OPERATING_STATUS.LIVE]
        ):
            self.coordinator.data["operating_status"] = OPERATING_STATUS_MAP[
                OPERATING_STATUS.IDLE
            ]
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
