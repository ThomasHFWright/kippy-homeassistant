"""Home Assistant constants and presentation labels for Kippy."""

from kippy_api.const import OPERATING_STATUS

DOMAIN = "kippy"

DEFAULT_ACTIVITY_REFRESH_DELAY = 2
DEFAULT_DEVICE_UPDATE_INTERVAL_MINUTES = 15
MIN_DEVICE_UPDATE_INTERVAL_MINUTES = 1
MAX_DEVICE_UPDATE_INTERVAL_MINUTES = 24 * 60

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

LABEL_EXPIRED = "Expired"

# Transient operating status used while live tracking is starting.
OPERATING_STATUS_STARTING_LIVE = "starting_live"

# Mapping of operating status codes to their human readable string.
OPERATING_STATUS_MAP: dict[int, str] = {
    OPERATING_STATUS.IDLE: "idle",
    OPERATING_STATUS.LIVE: "live",
    OPERATING_STATUS.ENERGY_SAVING: "energy_saving",
}

# Mapping of operating status strings back to their numeric codes.
OPERATING_STATUS_REVERSE_MAP: dict[str, int] = {
    value: key for key, value in OPERATING_STATUS_MAP.items()
}

# Mapping of ``petKind`` codes returned by the API to a human readable type.
PET_KIND_TO_TYPE: dict[str, str] = {
    "4": "dog",
    "3": "cat",
}
