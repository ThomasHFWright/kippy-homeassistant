"""Core HTTP client and authentication helpers for the Kippy API."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import ssl
from typing import Any, Dict, Mapping, Optional, cast

from aiohttp import ClientError, ClientResponseError, ClientSession

from ..const import (
    APP_IDENTITY,
    APP_IDENTITY_EVO,
    APP_VERSION,
    DEFAULT_HOST,
    DEVICE_NAME,
    ERROR_NO_AUTH_DATA,
    ERROR_NO_CREDENTIALS,
    ERROR_UNEXPECTED_AUTH_FAILURE,
    LOGIN_PATH,
    LOGIN_SENSITIVE_FIELDS,
    PHONE_COUNTRY_CODE,
    PLATFORM_DEVICE,
    REQUEST_HEADERS,
    RETURN_CODES_SUCCESS,
    RETURN_VALUES,
    TIMEZONE,
    TOKEN_DEVICE,
)
from ._utils import (
    _decode_json,
    _get_return_code,
    _redact,
    _redact_json,
    _return_code_error,
    _treat_401_as_success,
)

_LOGGER = logging.getLogger(__name__)


class BaseKippyApi:
    """Minimal Kippy API wrapper handling authentication and requests."""

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
    ) -> "BaseKippyApi":
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
        """Login to the Kippy API and cache the session."""

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
                    "Login request: %s",
                    json.dumps(_redact(payload, LOGIN_SENSITIVE_FIELDS)),
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
                        json.dumps(_redact(payload, LOGIN_SENSITIVE_FIELDS)),
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
                            json.dumps(_redact(payload, LOGIN_SENSITIVE_FIELDS)),
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
                        json.dumps(_redact(payload, LOGIN_SENSITIVE_FIELDS)),
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
                json.dumps(_redact(payload, LOGIN_SENSITIVE_FIELDS)),
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

    async def _authenticated_payload(
        self,
        *,
        identity: str | None = APP_IDENTITY,
        extra: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Return a payload seeded with the cached authentication tokens."""

        await self.ensure_login()

        if not self._auth:
            raise RuntimeError(ERROR_NO_AUTH_DATA)

        payload: Dict[str, Any] = {}

        if self.app_code is not None:
            payload["app_code"] = self.app_code
        if self.app_verification_code is not None:
            payload["app_verification_code"] = self.app_verification_code
        if identity is not None:
            payload["app_identity"] = identity
        if extra:
            payload.update(extra)

        return payload

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
                    _LOGGER.debug("%s request: %s", path, json.dumps(_redact(payload)))
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
                            json.dumps(_redact(payload)),
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
                    elif return_code in RETURN_CODES_SUCCESS:
                        return data
                    _LOGGER.debug(
                        "%s failed: return=%s request=%s response=%s",
                        path,
                        return_code,
                        json.dumps(_redact(payload)),
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
                    json.dumps(_redact(payload)),
                    err,
                )
                raise

        raise RuntimeError(ERROR_UNEXPECTED_AUTH_FAILURE)
