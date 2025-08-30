"""Simple API client for Kippy."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from aiohttp import ClientSession

DEFAULT_LOGIN_URL = "https://prod.kippyapi.eu/v2/login.php"

class KippyApi:
    """Minimal Kippy API wrapper handling authentication."""

    def __init__(self, session: ClientSession, login_url: str = DEFAULT_LOGIN_URL) -> None:
        """Initialize the API client."""
        self._session = session
        self._login_url = login_url
        self._auth: Optional[Dict[str, Any]] = None
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._email: Optional[str] = None
        self._password: Optional[str] = None

    @property
    def token(self) -> Optional[str]:
        """Return the cached session token if available."""
        return self._token

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

        async with self._session.post(
            self._login_url, data=json.dumps(payload), headers=headers
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        self._auth = data
        self._email = email
        self._password = password
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
