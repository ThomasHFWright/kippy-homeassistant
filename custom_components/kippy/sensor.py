"""Sensor platform for Kippy pets."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    LABEL_EXPIRED,
    LOCALIZATION_TECHNOLOGY_GPS,
    LOCALIZATION_TECHNOLOGY_LBS,
    PET_KIND_TO_TYPE,
)
from .coordinator import (
    KippyActivityCategoriesDataUpdateCoordinator,
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)
from .helpers import build_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Kippy sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    map_coordinators = hass.data[DOMAIN][entry.entry_id]["map_coordinators"]
    activity_coordinator: KippyActivityCategoriesDataUpdateCoordinator = hass.data[
        DOMAIN
    ][entry.entry_id]["activity_coordinator"]

    entities: list[SensorEntity] = []
    for pet in coordinator.data.get("pets", []):
        entities.append(KippyExpiredDaysSensor(coordinator, pet))
        entities.append(KippyIDSensor(coordinator, pet))
        entities.append(KippyIMEISensor(coordinator, pet))

        expired_days = pet.get("expired_days")
        is_expired = False
        try:
            is_expired = int(expired_days) >= 0
        except (TypeError, ValueError):
            pass

        if not is_expired:
            entities.append(KippyPetTypeSensor(coordinator, pet))
            map_coord = map_coordinators.get(pet["petID"])
            if map_coord:
                entities.append(KippyBatterySensor(map_coord, pet))
                entities.append(KippyLocalizationTechnologySensor(map_coord, pet))
                entities.append(KippyContactTimeSensor(map_coord, pet))
                entities.append(KippyNextCallTimeSensor(map_coord, pet))
                entities.append(KippyFixTimeSensor(map_coord, pet))
                entities.append(KippyGpsTimeSensor(map_coord, pet))
                entities.append(KippyLbsTimeSensor(map_coord, pet))
                entities.append(KippyOperatingStatusSensor(map_coord, pet))

            entities.extend(
                [
                    KippyStepsSensor(activity_coordinator, pet),
                    KippyCaloriesSensor(activity_coordinator, pet),
                    KippyRunSensor(activity_coordinator, pet),
                    KippyWalkSensor(activity_coordinator, pet),
                    KippySleepSensor(activity_coordinator, pet),
                    KippyRestSensor(activity_coordinator, pet),
                ]
            )

    async_add_entities(entities)


class _KippyBaseEntity(CoordinatorEntity[KippyDataUpdateCoordinator]):
    """Base entity for Kippy sensors."""

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet

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


class KippyExpiredDaysSensor(_KippyBaseEntity, SensorEntity):
    """Sensor for remaining service days."""

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Days Until Expiry" if pet_name else "Days Until Expiry"
        )
        self._attr_unique_id = f"{self._pet_id}_expired_days"

    @property
    def native_value(self) -> Any:
        days = self._pet_data.get("expired_days")
        if days is None:
            return None
        try:
            days = int(days)
        except (TypeError, ValueError):
            return None
        return abs(days) if days < 0 else LABEL_EXPIRED


class KippyPetTypeSensor(_KippyBaseEntity, SensorEntity):
    """Sensor for pet type."""

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Type" if pet_name else "Pet Type"
        self._attr_unique_id = f"{self._pet_id}_type"
        self._attr_translation_key = "pet_type"

    @property
    def native_value(self) -> str | None:
        kind = self._pet_data.get("petKind")
        return PET_KIND_TO_TYPE.get(str(kind))


class KippyIDSensor(_KippyBaseEntity, SensorEntity):
    """Diagnostic sensor for the Kippy device ID."""

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Kippy ID" if pet_name else "Kippy ID"
        self._attr_unique_id = f"{self._pet_id}_kippy_id"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return self._pet_data.get("kippyID") or self._pet_data.get("kippy_id")


class KippyIMEISensor(_KippyBaseEntity, SensorEntity):
    """Diagnostic sensor for the device IMEI."""

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} IMEI" if pet_name else "IMEI"
        self._attr_unique_id = f"{self._pet_id}_imei"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return self._pet_data.get("kippyIMEI")


class _KippyActivitySensor(
    CoordinatorEntity[KippyActivityCategoriesDataUpdateCoordinator], SensorEntity
):
    """Base class for daily activity sensors."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
        metric: str,
        name: str,
        unit: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        self._metric = metric
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} {name}" if pet_name else name
        self._attr_unique_id = f"{self._pet_id}_{metric}"
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._date: str | None = None

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._date:
            return {"date": self._date}
        return None

    @property
    def native_value(self) -> Any:
        activities = self.coordinator.get_activities(self._pet_id)
        if not activities:
            return None
        today = datetime.utcnow()
        value: Any = None

        # Cat trackers return data grouped by activity rather than by day.
        if isinstance(activities, list) and activities and "activity" in activities[0]:
            today_prefix = today.strftime("%Y%m%d")
            for activity in activities:
                if activity.get("activity") != self._metric:
                    continue
                total: float | int = 0
                for entry in activity.get("data", []):
                    time_caption = str(entry.get("timeCaption") or "")
                    if not time_caption.startswith(today_prefix):
                        continue
                    for key in (
                        "valueMinutes",
                        "value",
                        "count",
                        "minutes",
                        "duration",
                        "total",
                    ):
                        if key in entry:
                            try:
                                total += int(entry[key])
                            except (TypeError, ValueError):
                                try:
                                    total += float(entry[key])
                                except (TypeError, ValueError):
                                    pass
                            break
                value = total
                self._date = today.strftime("%Y-%m-%d")
                break
        else:
            today_str = today.strftime("%Y-%m-%d")
            for item in activities:
                item_date = (
                    item.get("date")
                    or item.get("day")
                    or item.get("date_time")
                    or item.get("datetime")
                )
                if item_date != today_str:
                    continue
                data = item.get(self._metric)
                if data is None and isinstance(item.get("activities"), list):
                    for cat in item["activities"]:
                        if (
                            cat.get("name") == self._metric
                            or cat.get("type") == self._metric
                        ):
                            data = (
                                cat.get("value")
                                or cat.get("count")
                                or cat.get("minutes")
                                or cat.get("duration")
                                or cat.get("total")
                            )
                            break
                if isinstance(data, dict):
                    for key in ("value", "count", "minutes", "duration", "total"):
                        if key in data:
                            data = data[key]
                            break
                value = data
                self._date = item_date
                break

        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None


class KippyStepsSensor(_KippyActivitySensor):
    """Sensor for daily step count."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet, "steps", "Steps", "steps")


class KippyCaloriesSensor(_KippyActivitySensor):
    """Sensor for daily calorie burn."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet, "calories", "Calories", "kcal")


class KippyRunSensor(_KippyActivitySensor):
    """Sensor for daily running minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet, "run", "Run", UnitOfTime.MINUTES)


class KippyWalkSensor(_KippyActivitySensor):
    """Sensor for daily walking minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet, "walk", "Walk", UnitOfTime.MINUTES)


class KippySleepSensor(_KippyActivitySensor):
    """Sensor for daily sleep minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet, "sleep", "Sleep", UnitOfTime.MINUTES)


class KippyRestSensor(_KippyActivitySensor):
    """Sensor for daily rest minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet, "rest", "Rest", UnitOfTime.MINUTES)


class KippyBatterySensor(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], SensorEntity
):
    """Sensor for device battery level."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Battery Level" if pet_name else "Battery Level"
        self._attr_unique_id = f"{self._pet_id}_battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

    @property
    def native_value(self) -> Any:
        val = self.coordinator.data.get("battery") if self.coordinator.data else None
        if val is None:
            val = self._pet_data.get("battery") or self._pet_data.get("batteryLevel")
        try:
            return int(val)
        except (TypeError, ValueError):
            return None


class KippyLocalizationTechnologySensor(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], SensorEntity
):
    """Sensor for the technology used to determine location."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Localization Technology"
            if pet_name
            else "Localization Technology"
        )
        self._attr_unique_id = f"{self._pet_id}_localization_technology"

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

    @property
    def native_value(self) -> Any:
        return (
            self.coordinator.data.get("localization_technology")
            if self.coordinator.data
            else None
        )


class _KippyBaseMapEntity(CoordinatorEntity[KippyMapDataUpdateCoordinator]):
    """Base entity for map-based sensors."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

    def _get_datetime(self, key: str) -> datetime | None:
        if not self.coordinator.data:
            return None
        ts = self.coordinator.data.get(key)
        try:
            return datetime.fromtimestamp(int(ts), timezone.utc)
        except (TypeError, ValueError, OSError):
            return None


class KippyContactTimeSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the last contact time with the server."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Contact Time" if pet_name else "Contact Time"
        self._attr_unique_id = f"{self._pet_id}_contact_time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self._get_datetime("contact_time")


class KippyNextCallTimeSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the next scheduled contact time."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Next Call Time" if pet_name else "Next Call Time"
        )
        self._attr_unique_id = f"{self._pet_id}_next_call_time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_translation_key = "next_call_time"

    @property
    def native_value(self) -> datetime | None:
        contact = (
            self.coordinator.data.get("contact_time") if self.coordinator.data else None
        )
        next_call = (
            self.coordinator.data.get("next_call_time")
            if self.coordinator.data
            else None
        )
        if contact and next_call:
            try:
                return datetime.fromtimestamp(
                    int(contact) + int(next_call), timezone.utc
                )
            except (TypeError, ValueError, OSError):
                return None
        return None


class KippyFixTimeSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the time of the current location fix."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Fix Time" if pet_name else "Fix Time"
        self._attr_unique_id = f"{self._pet_id}_fix_time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self._get_datetime("fix_time")


class KippyGpsTimeSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the timestamp of the latest GPS fix."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} {LOCALIZATION_TECHNOLOGY_GPS} Time"
            if pet_name
            else f"{LOCALIZATION_TECHNOLOGY_GPS} Time"
        )
        self._attr_unique_id = f"{self._pet_id}_gps_time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self._get_datetime("gps_time")


class KippyLbsTimeSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the timestamp of the latest LBS fix."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} {LOCALIZATION_TECHNOLOGY_LBS} Time"
            if pet_name
            else f"{LOCALIZATION_TECHNOLOGY_LBS} Time"
        )
        self._attr_unique_id = f"{self._pet_id}_lbs_time"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self._get_datetime("lbs_time")


class KippyOperatingStatusSensor(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], SensorEntity
):
    """Sensor indicating operating status."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_name = pet.get("petName")
        self._pet_data = pet
        self._attr_name = (
            f"{self._pet_name} Operating Status"
            if self._pet_name
            else "Operating Status"
        )
        self._attr_unique_id = f"{self._pet_id}_operating_status"
        self._attr_translation_key = "operating_status"

    @property
    def native_value(self) -> Any:
        return (
            self.coordinator.data.get("operating_status")
            if self.coordinator.data
            else None
        )

    @property
    def device_info(self) -> DeviceInfo:
        name = f"Kippy {self._pet_name}" if self._pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)
