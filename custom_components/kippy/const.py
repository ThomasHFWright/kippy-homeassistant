"""Constants for the Kippy integration."""
DOMAIN = "kippy"

# The integration exposes multiple entity types. The list is kept
# separate so ``async_forward_entry_setups`` can be used in ``__init__``.
PLATFORMS: list[str] = [
    "device_tracker",
    "sensor",
    "number",
    "switch",
    "binary_sensor",
    "button",
]

# Mapping of operating status codes returned by the API.
OPERATING_STATUS_IDLE = 1
OPERATING_STATUS_LIVE = 5
OPERATING_STATUS_POWER_SAVING = 18

# Name used by the API for low accuracy location updates
LOCALIZATION_TECHNOLOGY_LBS = "LBS (Low accuracy)"

# Mapping of ``petKind`` codes returned by the API to a human readable type.
PET_KIND_TO_TYPE: dict[str, str] = {
    "4": "Dog",
    "3": "Cat",
}
