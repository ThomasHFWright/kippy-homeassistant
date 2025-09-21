"""Sensor platform for Kippy pets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

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
from homeassistant.util import dt as dt_util
from homeassistant.util.location import distance as location_distance
from homeassistant.util.unit_conversion import DistanceConverter, DurationConverter

from .const import DOMAIN, LABEL_EXPIRED, LOCALIZATION_TECHNOLOGY_GPS, PET_KIND_TO_TYPE
from .coordinator import (
    KippyActivityCategoriesDataUpdateCoordinator,
    KippyDataUpdateCoordinator,
    KippyMapDataUpdateCoordinator,
)
from .entity import KippyMapEntity, KippyPetEntity
from .helpers import build_device_info, is_pet_subscription_active, update_pet_data

_TIME_UNITS = {
    UnitOfTime.MICROSECONDS,
    UnitOfTime.MILLISECONDS,
    UnitOfTime.SECONDS,
    UnitOfTime.MINUTES,
    UnitOfTime.HOURS,
    UnitOfTime.DAYS,
    UnitOfTime.WEEKS,
}


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

        if is_pet_subscription_active(pet):
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


class _KippyBaseEntity(KippyPetEntity, SensorEntity):
    """Base entity for Kippy sensors."""

    _preserve_fields = ("energySavingModePending",)


class KippyExpiredDaysSensor(_KippyBaseEntity):
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
            return DurationConverter.convert(remaining, self._source_unit, target_unit)
        return remaining


class KippyPetTypeSensor(_KippyBaseEntity):
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


class KippyIDSensor(_KippyBaseEntity):
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


class KippyIMEISensor(_KippyBaseEntity):
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


@dataclass(slots=True)
class ActivitySensorDescription:
    """Description of a daily activity sensor."""

    metric: str
    name: str
    unit: str | None = None
    device_class: SensorDeviceClass | str | None = None


class _KippyActivitySensor(
    CoordinatorEntity[KippyActivityCategoriesDataUpdateCoordinator], SensorEntity
):
    """Base class for daily activity sensors."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
        description: ActivitySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        self._description = description
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} {description.name}" if pet_name else description.name
        )
        self._attr_unique_id = f"{self._pet_id}_{description.metric}"
        if description.device_class:
            self._attr_device_class = description.device_class
        self._date: str | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return build_device_info(self._pet_id, self._pet_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._date:
            return {"date": self._date}
        return None

    @property
    def suggested_unit_of_measurement(self) -> str | None:
        if self._description.device_class == SensorDeviceClass.DURATION:
            return UnitOfTime.HOURS
        return None

    @property
    def native_value(self) -> Any:
        activities = self.coordinator.get_activities(self._pet_id)
        if not activities:
            return None
        today = dt_util.now()
        if self._activities_grouped_by_metric(activities):
            value, date_str = self._value_from_grouped_activities(activities, today)
        else:
            value, date_str = self._value_from_daily_entries(activities, today)
        if value is None:
            return None
        self._date = date_str
        return self._convert_activity_value(value)

    def _activities_grouped_by_metric(self, activities: Any) -> bool:
        return bool(
            isinstance(activities, list)
            and activities
            and isinstance(activities[0], dict)
            and "activity" in activities[0]
        )

    def _value_from_grouped_activities(
        self, activities: list[dict[str, Any]], today: datetime
    ) -> tuple[float | int | None, str | None]:
        today_prefix = today.strftime("%Y%m%d")
        for activity in activities:
            if activity.get("activity") != self._description.metric:
                continue
            total = 0.0
            for entry in activity.get("data", []):
                time_caption = str(entry.get("timeCaption") or "")
                if not time_caption.startswith(today_prefix):
                    continue
                numeric = self._extract_numeric_value(
                    entry,
                    (
                        "valueMinutes",
                        "value",
                        "count",
                        "minutes",
                        "duration",
                        "total",
                    ),
                )
                if numeric is not None:
                    total += numeric
            return total, today.strftime("%Y-%m-%d")
        return None, None

    def _value_from_daily_entries(
        self, activities: Any, today: datetime
    ) -> tuple[Any, str | None]:
        today_str = today.strftime("%Y-%m-%d")
        for item in activities:
            item_date = self._extract_date(item)
            if item_date != today_str:
                continue
            data = item.get(self._description.metric)
            if data is None and isinstance(item.get("activities"), list):
                data = self._value_from_activity_list(item["activities"])
            if isinstance(data, dict):
                data = self._extract_first_present(
                    data, ("value", "count", "minutes", "duration", "total")
                )
            return data, item_date
        return None, None

    def _value_from_activity_list(self, activities: list[dict[str, Any]]) -> Any:
        for entry in activities:
            if (
                entry.get("name") == self._description.metric
                or entry.get("type") == self._description.metric
            ):
                return self._extract_first_present(
                    entry, ("value", "count", "minutes", "duration", "total")
                )
        return None

    @staticmethod
    def _extract_date(item: Mapping[str, Any]) -> str | None:
        for key in ("date", "day", "date_time", "datetime"):
            value = item.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _extract_first_present(data: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            if key in data:
                return data[key]
        return None

    @staticmethod
    def _extract_numeric_value(
        data: Mapping[str, Any], keys: tuple[str, ...]
    ) -> float | None:
        for key in keys:
            if key not in data:
                continue
            value = data[key]
            try:
                return float(int(value))
            except (TypeError, ValueError):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return None

    def _convert_activity_value(self, value: Any) -> float | int | None:
        try:
            numeric: float | int = int(value)
        except (TypeError, ValueError):
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return None
        unit = self._description.unit
        if unit in _TIME_UNITS:
            target_unit = self.native_unit_of_measurement
            if target_unit != unit:
                return DurationConverter.convert(numeric, unit, target_unit)
        return numeric

    @property
    def native_unit_of_measurement(self) -> str | None:
        unit = self._description.unit
        if unit in _TIME_UNITS and self.hass:
            converted = self.hass.config.units.get_converted_unit(
                SensorDeviceClass.DURATION, unit
            )
            if converted:
                return converted
        return unit


class KippyStepsSensor(_KippyActivitySensor):
    """Sensor for daily step count."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription("steps", "Steps", "steps"),
        )


class KippyCaloriesSensor(_KippyActivitySensor):
    """Sensor for daily calorie burn."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription("calories", "Calories", "kcal"),
        )


class KippyRunSensor(_KippyActivitySensor):
    """Sensor for daily running time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "run", "Run", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class KippyWalkSensor(_KippyActivitySensor):
    """Sensor for daily walking time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "walk", "Walk", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class KippySleepSensor(_KippyActivitySensor):
    """Sensor for daily sleep time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "sleep", "Sleep", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class KippyRestSensor(_KippyActivitySensor):
    """Sensor for daily rest time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "rest", "Rest", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class KippyPlaySensor(_KippyActivitySensor):
    """Sensor for daily play time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "play", "Play", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class KippyRelaxSensor(_KippyActivitySensor):
    """Sensor for daily relax time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "relax", "Relax", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class KippyJumpsSensor(_KippyActivitySensor):
    """Sensor for daily jump count."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator, pet, ActivitySensorDescription("jumps", "Jumps", "jumps")
        )


class KippyClimbSensor(_KippyActivitySensor):
    """Sensor for daily climbing time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "climb", "Climb", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class KippyGroomingSensor(_KippyActivitySensor):
    """Sensor for daily grooming time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "grooming",
                "Grooming",
                UnitOfTime.MINUTES,
                SensorDeviceClass.DURATION,
            ),
        )


class KippyEatSensor(_KippyActivitySensor):
    """Sensor for daily eating time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "eat", "Eat", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class KippyDrinkSensor(_KippyActivitySensor):
    """Sensor for daily drinking time."""

    def __init__(
        self,
        coordinator: KippyActivityCategoriesDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator,
            pet,
            ActivitySensorDescription(
                "drink", "Drink", UnitOfTime.MINUTES, SensorDeviceClass.DURATION
            ),
        )


class _KippyBaseMapEntity(KippyMapEntity, SensorEntity):
    """Base entity for map-based sensors."""

    def _get_datetime(self, key: str) -> datetime | None:
        if not self.coordinator.data:
            return None
        ts = self.coordinator.data.get(key)
        try:
            return datetime.fromtimestamp(int(ts), timezone.utc)
        except (TypeError, ValueError, OSError):
            return None


class KippyBatterySensor(_KippyBaseMapEntity):
    """Sensor for device battery level."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        self._pet_id = pet["petID"]
        self._pet_data = pet
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Battery Level" if pet_name else "Battery Level"
        self._attr_unique_id = f"{self._pet_id}_battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Any:
        val = self.coordinator.data.get("battery") if self.coordinator.data else None
        if val is None:
            val = self._pet_data.get("battery") or self._pet_data.get("batteryLevel")
        try:
            return int(val)
        except (TypeError, ValueError):
            return None


class KippyLocalizationTechnologySensor(_KippyBaseMapEntity):
    """Sensor for the technology used to determine location."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
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
    def native_value(self) -> Any:
        return (
            self.coordinator.data.get("localization_technology")
            if self.coordinator.data
            else None
        )


class KippyLastContactSensor(_KippyBaseMapEntity):
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


class KippyNextContactSensor(_KippyBaseMapEntity):
    """Sensor for the next scheduled contact."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "next_contact"

    def __init__(
        self,
        coordinator: KippyMapDataUpdateCoordinator,
        base_coordinator: KippyDataUpdateCoordinator,
        pet: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, pet)
        self._base_coordinator = base_coordinator
        self.async_on_remove(
            base_coordinator.async_add_listener(self._handle_base_update)
        )
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Next Contact" if pet_name else "Next Contact"
        self._attr_unique_id = f"{self._pet_id}_next_contact"

    def _handle_base_update(self) -> None:
        self._pet_data = update_pet_data(
            self._base_coordinator.data.get("pets", []),
            self._pet_id,
            self._pet_data,
        )
        self.async_write_ha_state()

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


class KippyLastFixSensor(_KippyBaseMapEntity):
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


class KippyLastGpsFixSensor(_KippyBaseMapEntity):
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


class KippyLastLbsFixSensor(_KippyBaseMapEntity):
    """Sensor for the timestamp of the latest LBS fix."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = f"{pet_name} Last LBS Fix" if pet_name else "Last LBS Fix"
        self._attr_unique_id = f"{self._pet_id}_last_lbs_fix"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self._get_datetime("lbs_time")


class KippyOperatingStatusSensor(_KippyBaseMapEntity):
    """Sensor indicating operating status."""

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        self._pet_name = pet.get("petName")
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


class KippyEnergySavingStatusSensor(_KippyBaseEntity):
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


class KippyHomeDistanceSensor(_KippyBaseMapEntity):
    """Sensor for distance from Home Assistant's configured location."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "distance_from_home"

    def __init__(
        self, coordinator: KippyMapDataUpdateCoordinator, pet: dict[str, Any]
    ) -> None:
        super().__init__(coordinator, pet)
        pet_name = pet.get("petName")
        self._attr_name = (
            f"{pet_name} Distance from Home" if pet_name else "Distance from Home"
        )
        self._attr_unique_id = f"{self._pet_id}_distance_from_home"

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
        return DistanceConverter.convert(dist_m, UnitOfLength.METERS, target_unit)
