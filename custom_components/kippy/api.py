"""Simple API client for Kippy."""
from __future__ import annotations

import hashlib
import json
import logging
import ssl
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from aiohttp import ClientError, ClientResponseError, ClientSession

DEFAULT_HOST = "https://prod.kippyapi.eu"
LOGIN_PATH = "/v2/login.php"
GET_PETS_PATH = "/v2/GetPetKippyList.php"

_LOGGER = logging.getLogger(__name__)

class KippyApi:
    """Minimal Kippy API wrapper handling authentication."""

    def __init__(self, session: ClientSession, host: str = DEFAULT_HOST) -> None:
        """Initialize the API client."""
        self._session = session
        self._host = host.rstrip("/")
        self._auth: Optional[Dict[str, Any]] = None
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._email: Optional[str] = None
        self._password: Optional[str] = None
        self._app_code: Optional[str] = None
        self._app_verification_code: Optional[str] = None

        # Some Kippy servers use small Diffie-Hellman parameters which modern
        # OpenSSL rejects by default. Lower the security level and enable
        # legacy server connect to allow these connections.
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        self._ssl_context = ctx

    def _url(self, path: str) -> str:
        """Construct a full URL for a given API path."""
        return f"{self._host}{path}"

    @property
    def token(self) -> Optional[str]:
        """Return the cached session token if available."""
        return self._token

    @property
    def app_code(self) -> Optional[str]:
        """Return the app code from the login response."""
        return self._app_code

    @property
    def app_verification_code(self) -> Optional[str]:
        """Return the app verification code from the login response."""
        return self._app_verification_code

    async def login(self, email: str, password: str, force: bool = False) -> Dict[str, Any]:
        """Login to the Kippy API and cache the session.

        If a non-expired login session is already cached, it will be returned
        without performing a new network request unless ``force`` is True.
        """
        now = datetime.utcnow()
        if (
            not force
            and self._auth is not None
            and (self._token_expiry is None or now < self._token_expiry)
        ):
            return self._auth

        sha256_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
        md5_hex = hashlib.md5(password.encode("utf-8")).hexdigest()

        payload = {
            "login_email": email,
            "login_password_hash": sha256_hex,
            "login_password_hash_md5": md5_hex,
            "app_identity": "evo",
            "app_identity_evo": "1",
            "platform_device": "10",
            "app_version": "2.9.9",
            "timezone": 1.0,
            "phone_country_code": "1",
            "token_device": None,
            "device_name": "homeassistant",
        }

        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "application/json, */*;q=0.8",
            "User-Agent": "kippy-ha/0.1 (+aiohttp)",
        }

        try:
            async with self._session.post(
                self._url(LOGIN_PATH),
                data=json.dumps(payload),
                headers=headers,
                ssl=self._ssl_context,
            ) as resp:
                resp_text = await resp.text()
                try:
                    resp.raise_for_status()
                except ClientResponseError as err:
                    _LOGGER.debug(
                        "Login failed: status=%s request=%s response=%s",
                        err.status,
                        payload,
                        resp_text,
                    )
                    raise
                data = json.loads(resp_text)
                return_code = data.get("return")
                if return_code not in (0, "0"):
                    _LOGGER.debug(
                        "Login failed: return=%s request=%s response=%s",
                        return_code,
                        payload,
                        resp_text,
                    )
                    raise ClientResponseError(
                        resp.request_info,
                        resp.history,
                        status=401,
                        message=resp_text,
                        headers=resp.headers,
                    )
        except ClientError as err:
            _LOGGER.debug(
                "Error communicating with Kippy API: request=%s error=%s",
                payload,
                err,
            )
            raise

        self._auth = data
        self._email = email
        self._password = password
        self._app_code = data.get("app_code")
        self._app_verification_code = data.get("app_verification_code")
        self._token = data.get("token") or data.get("login_token") or data.get("auth_token")
        expires_in = data.get("token_expires_in") or data.get("expires_in")
        expire_at = data.get("token_expires_at") or data.get("expire_at")
        if expires_in is not None:
            self._token_expiry = now + timedelta(seconds=int(expires_in))
        elif expire_at is not None:
            self._token_expiry = datetime.utcfromtimestamp(int(expire_at))
        else:
            self._token_expiry = None

        return data

    async def ensure_login(self) -> None:
        """Ensure a valid login session is available."""
        if self._email is None or self._password is None:
            raise RuntimeError("No stored credentials; call login() first")
        await self.login(self._email, self._password)

    async def _post_with_refresh(
        self, path: str, payload: Dict[str, Any], headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """POST to the API and refresh login on authentication errors."""

        for attempt in range(2):
            try:
                async with self._session.post(
                    self._url(path),
                    data=json.dumps(payload),
                    headers=headers,
                    ssl=self._ssl_context,
                ) as resp:
                    resp_text = await resp.text()
                    try:
                        resp.raise_for_status()
                    except ClientResponseError as err:
                        _LOGGER.debug(
                            "%s failed: status=%s request=%s response=%s",
                            path,
                            err.status,
                            payload,
                            resp_text,
                        )
                        if err.status == 401 and attempt == 0:
                            await self.login(self._email, self._password, force=True)
                            retry_payload = {
                                "app_code": self._app_code,
                                "app_verification_code": self._app_verification_code,
                            }
                            if self._token is not None:
                                retry_payload["auth_token"] = self._token
                            payload.update(retry_payload)
                            continue
                        raise

                    data = json.loads(resp_text)
                    return_code = data.get("return")
                    if return_code not in (0, "0"):
                        _LOGGER.debug(
                            "%s failed: return=%s request=%s response=%s",
                            path,
                            return_code,
                            payload,
                            resp_text,
                        )
                        if str(return_code) == "6" and attempt == 0:
                            await self.login(self._email, self._password, force=True)
                            retry_payload = {
                                "app_code": self._app_code,
                                "app_verification_code": self._app_verification_code,
                            }
                            if self._token is not None:
                                retry_payload["auth_token"] = self._token
                            payload.update(retry_payload)
                            continue
                        raise ClientResponseError(
                            resp.request_info,
                            resp.history,
                            status=401,
                            message=resp_text,
                            headers=resp.headers,
                        )
                    return data
            except ClientError as err:
                _LOGGER.debug(
                    "Error communicating with Kippy API: request=%s error=%s",
                    payload,
                    err,
                )
                raise

        raise RuntimeError("Unexpected authentication failure")

    async def get_pet_kippy_list(self) -> list[dict[str, Any]]:
        """Retrieve the list of pets associated with the account."""
        await self.ensure_login()

        if not self._auth:
            raise RuntimeError("No authentication data available")

        payload = {
            "app_code": self._app_code,
            "app_verification_code": self._app_verification_code,
            "app_identity": "evo",
            "app_sub_identity": "evo",
        }
        if self._token:
            payload["auth_token"] = self._token

        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "application/json, */*;q=0.8",
            "User-Agent": "kippy-ha/0.1 (+aiohttp)",
        }
        data = await self._post_with_refresh(GET_PETS_PATH, payload, headers)
        return data.get("data", [])
