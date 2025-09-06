"""Constants for the Kippy integration."""
import json
from importlib import resources
from types import SimpleNamespace

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

# Default request headers.
REQUEST_HEADERS: dict[str, str] = {
    "Content-Type": "text/plain; charset=utf-8",
    "Accept": "application/json, */*;q=0.8",
    "User-Agent": "kippy-ha/0.1 (+aiohttp)",
}

# Default app/device configuration.
APP_IDENTITY = "evo"
APP_SUB_IDENTITY = "evo"
APP_IDENTITY_EVO = "1"
PLATFORM_DEVICE = "10"
APP_VERSION = "2.9.9"
TIMEZONE = 1.0
PHONE_COUNTRY_CODE = "1"
TOKEN_DEVICE = None
DEVICE_NAME = "homeassistant"
T_ID = 1

# Formula group and activity identifiers.
FORMULA_GROUP = SimpleNamespace(SUM="SUM")
ACTIVITY_ID = SimpleNamespace(ALL=0)

# Values for the API ``return`` field.
RETURN_VALUES = SimpleNamespace(
    SUCCESS=0,
    SUCCESS_TRUE=True,
    # Returned when a kippymap action is performed on a device without an
    # active subscription.
    SUBSCRIPTION_FAILURE=False,
    MALFORMED_REQUEST=[4, 13],
    AUTHORIZATION_EXPIRED=6,
    INVALID_CREDENTIALS=108,
)

# Return codes grouped by outcome.
RETURN_CODES_SUCCESS = {
    RETURN_VALUES.SUCCESS,
    RETURN_VALUES.SUCCESS_TRUE,
}

# Mapping of failure codes to human readable errors.
RETURN_CODE_ERRORS = {
    **{code: "Malformed request" for code in RETURN_VALUES.MALFORMED_REQUEST},
    RETURN_VALUES.AUTHORIZATION_EXPIRED: "Authorization expired",
    RETURN_VALUES.INVALID_CREDENTIALS: "Invalid credentials",
    RETURN_VALUES.SUBSCRIPTION_FAILURE: "Subscription inactive",
}

RETURN_CODES_FAILURE = set(RETURN_CODE_ERRORS)

# Fields to redact from logs.
SENSITIVE_LOG_FIELDS = {"app_code", "app_verification_code", "petID"}
LOGIN_SENSITIVE_FIELDS = {
    "login_email",
    "login_password_hash",
    "login_password_hash_md5",
}

# Credential values that should be treated as absent. Tests use this set to
# decide when to exercise a fake API rather than the real service.
MISSING_CREDENTIAL_PLACEHOLDERS = {None, "", "<REDACTED>"}

with resources.files(__package__).joinpath("translations/en.json").open(
    "r", encoding="utf-8"
) as _trans_file:
    _TRANSLATIONS = json.load(_trans_file)

ERROR_NO_CREDENTIALS = "No stored credentials; call login() first"
ERROR_UNEXPECTED_AUTH_FAILURE = "Unexpected authentication failure"
ERROR_NO_AUTH_DATA = "No authentication data available"
LABEL_EXPIRED = "Expired"

# Mapping of operating status codes returned by the API.
OPERATING_STATUS = SimpleNamespace(
    IDLE=1,
    LIVE=5,
    ENERGY_SAVING=18,
)

# Mapping of operating status codes to their human readable string.
OPERATING_STATUS_MAP: dict[int, str] = {
    OPERATING_STATUS.IDLE: "idle",
    OPERATING_STATUS.LIVE: "live",
    OPERATING_STATUS.ENERGY_SAVING: "energy_saving",
}

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
    "4": "dog",
    "3": "cat",
}
