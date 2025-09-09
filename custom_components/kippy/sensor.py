"""Sensor platform for Kippy pets."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.location import distance as location_distance
from homeassistant.util.unit_conversion import DistanceConverter, DurationConverter

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
            entities.append(KippyEnergySavingStatusSensor(coordinator, pet))
            entities.append(KippyPetTypeSensor(coordinator, pet))
            map_coord = map_coordinators.get(pet["petID"])
            if map_coord:
                entities.append(KippyBatterySensor(map_coord, pet))
                entities.append(KippyLocalizationTechnologySensor(map_coord, pet))
                entities.append(KippyLastContactSensor(map_coord, pet))
                entities.append(KippyNextContactSensor(map_coord, coordinator, pet))
                entities.append(KippyLastFixSensor(map_coord, pet))
                entities.append(KippyLastGpsFixSensor(map_coord, pet))
                entities.append(KippyLastLbsFixSensor(map_coord, pet))
                entities.append(KippyOperatingStatusSensor(map_coord, pet))
                entities.append(KippyHomeDistanceSensor(map_coord, pet))

            entities.extend(
                [
                    KippyStepsSensor(activity_coordinator, pet),
                    KippyCaloriesSensor(activity_coordinator, pet),
                    KippyRunSensor(activity_coordinator, pet),
                    KippyWalkSensor(activity_coordinator, pet),
                    KippySleepSensor(activity_coordinator, pet),
                    KippyRestSensor(activity_coordinator, pet),
                    KippyPlaySensor(activity_coordinator, pet),
                    KippyRelaxSensor(activity_coordinator, pet),
                    KippyJumpsSensor(activity_coordinator, pet),
                    KippyClimbSensor(activity_coordinator, pet),
                    KippyGroomingSensor(activity_coordinator, pet),
                    KippyEatSensor(activity_coordinator, pet),
                    KippyDrinkSensor(activity_coordinator, pet),
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
                if (
                    self._pet_data.get("energySavingModePending")
                    and "energySavingModePending" not in pet
                ):
                    pet["energySavingModePending"] = self._pet_data[
                        "energySavingModePending"
                    ]
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
        self._source_unit = UnitOfTime.DAYS

    @property
    def native_unit_of_measurement(self) -> str:
        days = self._pet_data.get("expired_days")
        try:
            days = int(days)
        except (TypeError, ValueError):
            return None
        if days >= 0:
            return None
        if self.hass:
            unit = self.hass.config.units.get_converted_unit(
                SensorDeviceClass.DURATION, self._source_unit
            )
            if unit:
                return unit
        return self._source_unit

    @property
    def native_value(self) -> Any:
        days = self._pet_data.get("expired_days")
        if days is None:
            return None
        try:
            days = int(days)
        except (TypeError, ValueError):
            return None
        if days >= 0:
            return LABEL_EXPIRED
        remaining = abs(days)
        target_unit = self.native_unit_of_measurement or self._source_unit
        if target_unit != self._source_unit:
            return DurationConverter.convert(
                remaining, self._source_unit, target_unit
            )
        return remaining


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
        device_class: SensorDeviceClass | str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        self._metric = metric
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} {name}" if pet_name else name
        self._attr_unique_id = f"{self._pet_id}_{metric}"
        self._source_unit = unit
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = SensorStateClass.MEASUREMENT
        if device_class:
            self._attr_device_class = device_class
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
        today = datetime.now().astimezone()
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
            numeric: float | int = int(value)
        except (TypeError, ValueError):
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return None
        if self._source_unit in {
            UnitOfTime.MICROSECONDS,
            UnitOfTime.MILLISECONDS,
            UnitOfTime.SECONDS,
            UnitOfTime.MINUTES,
            UnitOfTime.HOURS,
            UnitOfTime.DAYS,
            UnitOfTime.WEEKS,
        }:
            target_unit = self.native_unit_of_measurement
            if target_unit != self._source_unit:
                return DurationConverter.convert(
                    numeric, self._source_unit, target_unit
                )
        return numeric

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._source_unit in {
            UnitOfTime.MICROSECONDS,
            UnitOfTime.MILLISECONDS,
            UnitOfTime.SECONDS,
            UnitOfTime.MINUTES,
            UnitOfTime.HOURS,
            UnitOfTime.DAYS,
            UnitOfTime.WEEKS,
        }:
            if self.hass:
                unit = self.hass.config.units.get_converted_unit(
                    SensorDeviceClass.DURATION, self._source_unit
                )
                if unit:
                    return unit
        return self._source_unit


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
        super().__init__(
            coordinator,
            pet,
            "run",
            "Run",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippyWalkSensor(_KippyActivitySensor):
    """Sensor for daily walking minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "walk",
            "Walk",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippySleepSensor(_KippyActivitySensor):
    """Sensor for daily sleep minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "sleep",
            "Sleep",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippyRestSensor(_KippyActivitySensor):
    """Sensor for daily rest minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "rest",
            "Rest",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippyPlaySensor(_KippyActivitySensor):
    """Sensor for daily play minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "play",
            "Play",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippyRelaxSensor(_KippyActivitySensor):
    """Sensor for daily relax minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "relax",
            "Relax",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippyJumpsSensor(_KippyActivitySensor):
    """Sensor for daily jump count."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet, "jumps", "Jumps", "jumps")


class KippyClimbSensor(_KippyActivitySensor):
    """Sensor for daily climb minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "climb",
            "Climb",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippyGroomingSensor(_KippyActivitySensor):
    """Sensor for daily grooming minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "grooming",
            "Grooming",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippyEatSensor(_KippyActivitySensor):
    """Sensor for daily eating minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "eat",
            "Eat",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


class KippyDrinkSensor(_KippyActivitySensor):
    """Sensor for daily drinking minutes."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            "drink",
            "Drink",
            UnitOfTime.MINUTES,
            SensorDeviceClass.DURATION,
        )


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


class KippyLastContactSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the time of the last contact with the server."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Last Contact" if pet_name else "Last Contact"
        self._attr_unique_id = f"{self._pet_id}_last_contact"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self._get_datetime("contact_time")


class KippyNextContactSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the next scheduled contact."""

    def __init__(
        self,
        coordinator: KippyMapDataUpdateCoordinator,
        base_coordinator: KippyDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet)
        self._base_coordinator = base_coordinator
        self._base_unsub: Callable[[], None] | None = None
        self._base_unsub = base_coordinator.async_add_listener(
            self._handle_base_update
        )
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Next Contact" if pet_name else "Next Contact"
        self._attr_unique_id = f"{self._pet_id}_next_contact"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_translation_key = "next_contact"

    def _handle_base_update(self) -> None:
        for pet in self._base_coordinator.data.get("pets", []):
            if pet.get("petID") == self._pet_id:
                self._pet_data = pet
                break
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._base_unsub:
            self._base_unsub()
            self._base_unsub = None
        await super().async_will_remove_from_hass()

    @property
    def native_value(self) -> datetime | None:
        contact = (
            self.coordinator.data.get("contact_time") if self.coordinator.data else None
        )
        update_frequency = self._pet_data.get("updateFrequency")
        if contact is None or update_frequency is None:
            return None
        try:
            return datetime.fromtimestamp(
                int(contact) + int(update_frequency) * 3600, timezone.utc
            )
        except (TypeError, ValueError, OSError):
            return None


class KippyLastFixSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the time of the last location fix."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Last Fix" if pet_name else "Last Fix"
        self._attr_unique_id = f"{self._pet_id}_last_fix"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self._get_datetime("fix_time")


class KippyLastGpsFixSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the timestamp of the latest GPS fix."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Last {LOCALIZATION_TECHNOLOGY_GPS} Fix"
            if pet_name
            else f"Last {LOCALIZATION_TECHNOLOGY_GPS} Fix"
        )
        self._attr_unique_id = f"{self._pet_id}_last_gps_fix"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self._get_datetime("gps_time")


class KippyLastLbsFixSensor(_KippyBaseMapEntity, SensorEntity):
    """Sensor for the timestamp of the latest LBS fix."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Last LBS Fix" if pet_name else "Last LBS Fix"
        )
        self._attr_unique_id = f"{self._pet_id}_last_lbs_fix"
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


class KippyEnergySavingStatusSensor(_KippyBaseEntity, SensorEntity):
    """Sensor indicating energy saving status."""

    _attr_translation_key = "energy_saving_status"

    def __init__(
        self, coordinator: KippyDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Energy Saving Status" if pet_name else "Energy Saving Status"
        )
        self._attr_unique_id = f"{self._pet_id}_energy_saving_status"

    @property
    def native_value(self) -> str:
        pending = bool(self._pet_data.get("energySavingModePending"))
        value = self._pet_data.get("energySavingMode")
        try:
            is_on = bool(int(value))
        except (TypeError, ValueError):
            is_on = bool(value)
        if pending:
            return "on_pending" if is_on else "off_pending"
        return "on" if is_on else "off"


class KippyHomeDistanceSensor(
    CoordinatorEntity[KippyMapDataUpdateCoordinator], SensorEntity
):
    """Sensor for distance from Home Assistant's configured location."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "distance_from_home"

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Distance from Home" if pet_name else "Distance from Home"
        )
        self._attr_unique_id = f"{self._pet_id}_distance_from_home"

    @property
    def device_info(self) -> DeviceInfo:
        pet_name = self._pet_data.get("petName")
        name = f"Kippy {pet_name}" if pet_name else "Kippy"
        return build_device_info(self._pet_id, self._pet_data, name)

    @property
    def native_unit_of_measurement(self) -> str:
        unit = self.hass.config.units.length_unit
        return UnitOfLength.METERS if unit == UnitOfLength.KILOMETERS else unit

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        lat = self.coordinator.data.get("gps_latitude")
        lon = self.coordinator.data.get("gps_longitude")
        if lat is None or lon is None:
            return None
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            return None
        dist_m = location_distance(
            self.hass.config.latitude, self.hass.config.longitude, lat_f, lon_f
        )
        if dist_m is None:
            return None
        target_unit = self.native_unit_of_measurement
        return DistanceConverter.convert(
            dist_m, UnitOfLength.METERS, target_unit
        )
