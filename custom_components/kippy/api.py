"""Simple API client for Kippy."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import ssl
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, cast

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import (
    ACTIVITY_ID,
    APP_IDENTITY,
    APP_IDENTITY_EVO,
    APP_SUB_IDENTITY,
    APP_VERSION,
    DEFAULT_HOST,
    DEVICE_NAME,
    ERROR_NO_AUTH_DATA,
    ERROR_NO_CREDENTIALS,
    ERROR_UNEXPECTED_AUTH_FAILURE,
    FORMULA_GROUP,
    GET_ACTIVITY_CATEGORIES_PATH,
    GET_PETS_PATH,
    KIPPYMAP_ACTION_PATH,
    LOCALIZATION_TECHNOLOGY_MAP,
    LOGIN_PATH,
    LOGIN_SENSITIVE_FIELDS,
    PHONE_COUNTRY_CODE,
    PLATFORM_DEVICE,
    REQUEST_HEADERS,
    RETURN_CODE_ERRORS,
    RETURN_CODES_SUCCESS,
    RETURN_VALUES,
    SENSITIVE_LOG_FIELDS,
    T_ID,
    TIMEZONE,
    TOKEN_DEVICE,
)

_LOGGER = logging.getLogger(__name__)


def _redact_tree(data: Any, sensitive: set[str]) -> Any:
    """Recursively redact sensitive fields within ``data``."""
    if isinstance(data, dict):
        return {
            k: ("***" if k in sensitive else _redact_tree(v, sensitive))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_redact_tree(item, sensitive) for item in data]
    return data


def _redact(data: Dict[str, Any], extra: set[str] | None = None) -> Dict[str, Any]:
    """Return a copy of ``data`` with sensitive fields redacted."""
    sensitive = SENSITIVE_LOG_FIELDS | (extra or set())
    return cast(Dict[str, Any], _redact_tree(data, sensitive))


def _redact_json(text: str) -> str:
    """Redact sensitive fields from JSON ``text`` if possible."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(_redact_tree(data, SENSITIVE_LOG_FIELDS))


def _decode_json(text: str) -> Dict[str, Any] | None:
    """Decode ``text`` as JSON, returning ``None`` on failure."""
    try:
        return cast(Dict[str, Any], json.loads(text))
    except json.JSONDecodeError:
        return None


def _get_return_code(data: Dict[str, Any] | None) -> int | bool | str | None:
    """Extract the API ``return`` code from ``data`` if present.

    The ``return`` value is inconsistently typed by the API, sometimes being
    returned as a string such as ``"0"`` or ``"108"``. Normalizing the value to
    ``int`` ensures comparisons against numeric constants remain valid regardless
    of the original type. Boolean values are preserved as-is.
    """
    if not isinstance(data, dict):
        return None
    if (code := data.get("return")) is None:
        code = data.get("Result")
    if code is None:
        return None
    if isinstance(code, bool):
        return code
    try:
        return int(code)
    except (TypeError, ValueError):
        return code


def _return_code_error(code: Any) -> str:
    """Return a human readable error for ``code``.

    If ``code`` is unknown, include the code in the message.
    """
    if (msg := RETURN_CODE_ERRORS.get(code)) is not None:
        return f"{msg} (code {code})"
    return f"Unknown error code {code}"


def _treat_401_as_success(path: str, data: Dict[str, Any]) -> bool:
    """Determine if a 401 response should be treated as a success."""
    return_code = _get_return_code(data)
    if return_code is None:
        _LOGGER.debug("%s returned HTTP 401 with data, assuming success", path)
        return True
    if isinstance(return_code, bool):
        if return_code:
            return True
        _LOGGER.debug("%s returned Result=%s, treating as failure", path, return_code)
        return False
    if return_code not in RETURN_CODES_SUCCESS:
        _LOGGER.debug("%s returned Result=%s, treating as failure", path, return_code)
        return False
    return True


def _weeks_param(start: datetime, end: datetime) -> str:
    """Return a JSON list of ISO weeks between ``start`` and ``end``."""
    weeks_list: list[dict[str, str]] = []
    current = start
    while current <= end:
        year, week, _ = current.isocalendar()
        entry = {"year": str(year), "number": str(week)}
        if entry not in weeks_list:
            weeks_list.append(entry)
        current += timedelta(days=1)
    return json.dumps(weeks_list)


def _tz_hours(dt: datetime) -> float:
    """Return timezone offset in hours for ``dt``."""
    tz_offset = dt.utcoffset() or timedelta()
    return tz_offset.total_seconds() / 3600


class KippyApi:
    """Minimal Kippy API wrapper handling authentication."""

    def __init__(
        self,
        session: ClientSession,
        host: str = DEFAULT_HOST,
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._host = host.rstrip("/")
        self._auth: Optional[Dict[str, Any]] = None
        self._credentials: tuple[str, str] | None = None

        self._ssl_context = ssl_context

    @classmethod
    async def async_create(
        cls, session: ClientSession, host: str = DEFAULT_HOST
    ) -> "KippyApi":
        """Create an instance of the API client with an SSL context."""
        loop = asyncio.get_running_loop()
        ctx = await loop.run_in_executor(None, ssl.create_default_context)
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        return cls(session, host, ctx)

    def _url(self, path: str) -> str:
        """Construct a full URL for a given API path."""
        return f"{self._host}{path}"

    @property
    def app_code(self) -> Optional[str]:
        """Return the app code from the login response."""
        return cast(Optional[str], self._auth.get("app_code") if self._auth else None)

    @property
    def app_verification_code(self) -> Optional[str]:
        """Return the app verification code from the login response."""
        return cast(
            Optional[str],
            self._auth.get("app_verification_code") if self._auth else None,
        )

    async def login(
        self, email: str, password: str, force: bool = False
    ) -> Dict[str, Any]:
        """Login to the Kippy API and cache the session.

        If a non-expired login session is already cached, it will be returned
        without performing a new network request unless ``force`` is True.
        """
        if not force and self._auth is not None:
            return self._auth

        payload = {
            "login_email": email,
            "login_password_hash": hashlib.sha256(password.encode("utf-8")).hexdigest(),
            "login_password_hash_md5": hashlib.md5(
                password.encode("utf-8")
            ).hexdigest(),
            "app_identity": APP_IDENTITY,
            "app_identity_evo": APP_IDENTITY_EVO,
            "platform_device": PLATFORM_DEVICE,
            "app_version": APP_VERSION,
            "timezone": TIMEZONE,
            "phone_country_code": PHONE_COUNTRY_CODE,
            "token_device": TOKEN_DEVICE,
            "device_name": DEVICE_NAME,
        }

        try:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(
                    "Login request: %s", _redact(payload, LOGIN_SENSITIVE_FIELDS)
                )
            async with self._session.post(
                self._url(LOGIN_PATH),
                data=json.dumps(payload),
                headers=REQUEST_HEADERS,
                ssl=self._ssl_context,
            ) as resp:
                resp_text = await resp.text()
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug("Login response: %s", _redact_json(resp_text))
                try:
                    resp.raise_for_status()
                except ClientResponseError as err:
                    _LOGGER.debug(
                        "Login failed: status=%s request=%s response=%s",
                        err.status,
                        _redact(payload, LOGIN_SENSITIVE_FIELDS),
                        _redact_json(resp_text),
                    )
                    raise
                data = json.loads(resp_text)
                return_code = _get_return_code(data)
                if isinstance(return_code, bool):
                    if not return_code:
                        _LOGGER.debug(
                            "Login failed: return=%s request=%s response=%s",
                            return_code,
                            _redact(payload, LOGIN_SENSITIVE_FIELDS),
                            _redact_json(resp_text),
                        )
                        raise ClientResponseError(
                            resp.request_info,
                            resp.history,
                            status=401,
                            message=_return_code_error(return_code),
                            headers=resp.headers,
                        )
                elif return_code not in RETURN_CODES_SUCCESS:
                    _LOGGER.debug(
                        "Login failed: return=%s request=%s response=%s",
                        return_code,
                        _redact(payload, LOGIN_SENSITIVE_FIELDS),
                        _redact_json(resp_text),
                    )
                    raise ClientResponseError(
                        resp.request_info,
                        resp.history,
                        status=401,
                        message=_return_code_error(return_code),
                        headers=resp.headers,
                    )
        except ClientError as err:
            _LOGGER.debug(
                "Error communicating with Kippy API: request=%s error=%s",
                _redact(payload, LOGIN_SENSITIVE_FIELDS),
                err,
            )
            raise

        self._auth = data
        self._credentials = (email, password)
        return data

    async def ensure_login(self) -> None:
        """Ensure a valid login session is available."""
        if self._credentials is None:
            raise RuntimeError(ERROR_NO_CREDENTIALS)
        email, password = self._credentials
        await self.login(email, password)

    async def _refresh_login(self, payload: Dict[str, Any]) -> None:
        """Refresh login credentials and update ``payload`` with new codes."""
        if self._credentials is None:
            raise RuntimeError(ERROR_NO_CREDENTIALS)
        email, password = self._credentials
        await self.login(email, password, force=True)
        retry_payload = {
            "app_code": self.app_code,
            "app_verification_code": self.app_verification_code,
        }
        payload.update(retry_payload)

    async def _post_with_refresh(
        self, path: str, payload: Dict[str, Any], headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """POST to the API and refresh login on authentication errors."""
        for attempt in range(2):
            try:
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug("%s request: %s", path, _redact(payload))
                async with self._session.post(
                    self._url(path),
                    data=json.dumps(payload),
                    headers=headers,
                    ssl=self._ssl_context,
                ) as resp:
                    resp_text = await resp.text()
                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        _LOGGER.debug("%s response: %s", path, _redact_json(resp_text))
                    data = _decode_json(resp_text)
                    if (
                        resp.status == 401
                        and isinstance(data, dict)
                        and _treat_401_as_success(path, data)
                    ):
                        return data
                    try:
                        resp.raise_for_status()
                    except ClientResponseError as err:
                        _LOGGER.debug(
                            "%s failed: status=%s request=%s response=%s",
                            path,
                            err.status,
                            _redact(payload),
                            _redact_json(resp_text),
                        )
                        if err.status == 401 and attempt == 0:
                            await self._refresh_login(payload)
                            continue
                        raise
                    data = data or json.loads(resp_text)
                    return_code = _get_return_code(data)
                    if isinstance(return_code, bool):
                        if return_code:
                            return data
                    elif return_code is None or return_code in RETURN_CODES_SUCCESS:
                        return data
                    _LOGGER.debug(
                        "%s failed: return=%s request=%s response=%s",
                        path,
                        return_code,
                        _redact(payload),
                        _redact_json(resp_text),
                    )
                    if (
                        return_code == RETURN_VALUES.AUTHORIZATION_EXPIRED
                        and attempt == 0
                    ):
                        await self._refresh_login(payload)
                        continue
                    raise ClientResponseError(
                        resp.request_info,
                        resp.history,
                        status=401,
                        message=_return_code_error(return_code),
                        headers=resp.headers,
                    )
            except ClientError as err:
                _LOGGER.debug(
                    "Error communicating with Kippy API: request=%s error=%s",
                    _redact(payload),
                    err,
                )
                raise

        raise RuntimeError(ERROR_UNEXPECTED_AUTH_FAILURE)

    async def get_pet_kippy_list(self) -> list[dict[str, Any]]:
        """Retrieve the list of pets associated with the account."""
        await self.ensure_login()

        if not self._auth:
            raise RuntimeError(ERROR_NO_AUTH_DATA)

        payload = {
            "app_code": self.app_code,
            "app_verification_code": self.app_verification_code,
            "app_identity": APP_IDENTITY,
            "app_sub_identity": APP_SUB_IDENTITY,
        }

        data = await self._post_with_refresh(GET_PETS_PATH, payload, REQUEST_HEADERS)
        return data.get("data", [])

    async def kippymap_action(
        self,
        kippy_id: int,
        do_sms: bool = True,
        app_action: int | None = None,
        geofence_id: int | None = None,
    ) -> Dict[str, Any]:
        """Perform a kippymap action for a specific device."""

        await self.ensure_login()

        if not self._auth:
            raise RuntimeError(ERROR_NO_AUTH_DATA)

        payload: Dict[str, Any] = {
            "app_code": self.app_code,
            "app_verification_code": self.app_verification_code,
            "app_identity": APP_IDENTITY,
            "kippy_id": kippy_id,
            "do_sms": int(do_sms),
        }
        if app_action is not None:
            payload["app_action"] = app_action
        if geofence_id is not None:
            payload["geofence_id"] = geofence_id

        data = await self._post_with_refresh(
            KIPPYMAP_ACTION_PATH, payload, REQUEST_HEADERS
        )

        payload = data.get("data")
        if not isinstance(payload, dict):
            payload = dict(data)

        # Extract primary GPS location details
        lat = payload.pop("lat", None)
        if lat is not None:
            payload["gps_latitude"] = lat
        lng = payload.pop("lng", None)
        if lng is not None:
            payload["gps_longitude"] = lng
        radius = payload.pop("radius", None)
        if radius is not None:
            payload["gps_accuracy"] = radius
        altitude = payload.pop("altitude", None)
        if altitude is not None:
            payload["gps_altitude"] = altitude

        tech = payload.get("localization_tecnology")
        if tech is not None:
            payload["localization_technology"] = LOCALIZATION_TECHNOLOGY_MAP.get(
                str(tech), str(tech)
            )

        return payload

    async def get_activity_categories(
        self,
        pet_id: int,
        from_date: str,
        to_date: str,
        time_division: int,
        _weeks: int,
    ) -> Dict[str, Any]:
        """Retrieve activity categories for a pet.

        The API changed parameter names and now expects timestamps and a list of
        ISO weeks.  ``from_date`` and ``to_date`` are provided as ``YYYY-MM-DD``
        strings and converted internally to UNIX timestamps.  The ``_weeks``
        argument is kept for backwards compatibility and currently ignored.
        """

        await self.ensure_login()

        if not self._auth:
            raise RuntimeError(ERROR_NO_AUTH_DATA)

        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d")

        start_ts = int(
            start.replace(tzinfo=datetime.now().astimezone().tzinfo).timestamp()
        )
        end_ts = int(end.replace(tzinfo=datetime.now().astimezone().tzinfo).timestamp())

        tz_hours = _tz_hours(start.replace(tzinfo=datetime.now().astimezone().tzinfo))

        weeks_param = _weeks_param(start, end)

        time_divisions = {1: "h", 2: "d", 3: "w"}.get(time_division, "h")

        payload: Dict[str, Any] = {
            "app_code": self.app_code,
            "app_verification_code": self.app_verification_code,
            "app_identity": APP_IDENTITY,
            "petID": pet_id,
            "activityID": ACTIVITY_ID.ALL,
            "fromDate": start_ts,
            "toDate": end_ts,
            "timeDivisions": time_divisions,
            "formulaGroup": FORMULA_GROUP.SUM,
            "tID": T_ID,
            "timezone": tz_hours,
            "weeks": weeks_param,
        }

        data = await self._post_with_refresh(
            GET_ACTIVITY_CATEGORIES_PATH, payload, REQUEST_HEADERS
        )

        if isinstance(data, dict):
            if "data" in data:
                payload = data.get("data") or {}
            else:
                payload = {
                    "activities": data.get("ActivitiesData"),
                    "avg": data.get("AVGData"),
                    "health": data.get("HealthData"),
                }
        else:
            payload = {}

        return {
            "activities": payload.get("activities"),
            "avg": payload.get("avg"),
            "health": payload.get("health"),
        }
