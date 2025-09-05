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

# API endpoints.
DEFAULT_HOST = "https://prod.kippyapi.eu"
LOGIN_PATH = "/v2/login.php"
GET_PETS_PATH = "/v2/GetPetKippyList.php"
KIPPYMAP_ACTION_PATH = "/v2/kippymap_action.php"
GET_ACTIVITY_CATEGORIES_PATH = "/v2/vita/get_activities_cat.php"

# Fields to redact from logs.
SENSITIVE_LOG_FIELDS = {"app_code", "app_verification_code", "petID", "auth_token"}
LOGIN_SENSITIVE_FIELDS = {
    "login_email",
    "login_password_hash",
    "login_password_hash_md5",
}

# Mapping of operating status codes returned by the API.
OPERATING_STATUS_IDLE = 1
OPERATING_STATUS_LIVE = 5
OPERATING_STATUS_POWER_SAVING = 18

# Names used by the API for location technologies.
LOCALIZATION_TECHNOLOGY_LBS = "LBS (Low accuracy)"
LOCALIZATION_TECHNOLOGY_GPS = "GPS"
LOCALIZATION_TECHNOLOGY_WIFI = "Wifi"

# Mapping of localization technology codes returned by the API.
LOCALIZATION_TECHNOLOGY_MAP: dict[str, str] = {
    "1": LOCALIZATION_TECHNOLOGY_LBS,
    "2": LOCALIZATION_TECHNOLOGY_GPS,
    "3": LOCALIZATION_TECHNOLOGY_WIFI,
}

# Mapping of ``petKind`` codes returned by the API to a human readable type.
PET_KIND_TO_TYPE: dict[str, str] = {
    "4": "Dog",
    "3": "Cat",
}

