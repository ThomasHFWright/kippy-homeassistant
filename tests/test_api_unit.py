"""Unit tests for the modular Kippy API client."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientResponseError

from custom_components.kippy.api import (
    KippyApi,
    _decode_json,
    _get_return_code,
    _redact,
    _redact_json,
    _return_code_error,
    _treat_401_as_success,
    _tz_hours,
    _weeks_param,
)
from custom_components.kippy.const import REQUEST_HEADERS, RETURN_VALUES


class _CM:
    """Simple async context manager for fake responses."""

    def __init__(self, resp):
        self.resp = resp

    async def __aenter__(self):
        """Return the wrapped fake response."""

        return self.resp

    async def __aexit__(self, exc_type, exc, tb):
        """Exit without suppressing exceptions."""

        return False


class _FakeResp:
    """Stand-in response used for exercising request handling."""

    def __init__(self, status: int, text: str = "{}"):
        self.status = status
        self._text = text
        self.headers = {}
        self.request_info = MagicMock()
        self.history: tuple = ()

    async def text(self) -> str:  # noqa: D401
        """Return the canned response text."""

        return self._text

    def raise_for_status(self) -> None:
        """Raise a :class:`ClientResponseError` for HTTP errors."""

        if self.status >= 400:
            raise ClientResponseError(
                self.request_info,
                self.history,
                status=self.status,
                message="err",
                headers={},
            )


@pytest.mark.asyncio
async def test_login_handles_return_code_failure() -> None:
    """Login raises for unsuccessful return codes."""

    resp = _FakeResp(200, '{"return": 108}')
    session = MagicMock()
    session.post.return_value = _CM(resp)

    api = KippyApi(session)
    with pytest.raises(ClientResponseError):
        await api.login("a", "b", force=True)


@pytest.mark.asyncio
async def test_post_with_refresh_retries_on_expired() -> None:
    """post_with_refresh refreshes login once then returns data."""

    resp1 = _FakeResp(401, '{"return": %d}' % RETURN_VALUES.AUTHORIZATION_EXPIRED)
    resp2 = _FakeResp(200, '{"return": 0, "data": {"ok": true}}')
    session = MagicMock()
    session.post.side_effect = [_CM(resp1), _CM(resp2)]

    api = KippyApi(session)
    api.cache_authentication(
        {"token": 1, "app_code": "1", "app_verification_code": "2"},
        credentials=("e", "p"),
    )

    async def fake_login(*_args, **_kwargs):
        return {"app_code": "1", "app_verification_code": "2"}

    api.login = AsyncMock(side_effect=fake_login)  # type: ignore[assignment]

    result = await api.post_with_refresh("/x", {"a": 1}, REQUEST_HEADERS)
    assert result["data"]["ok"] is True


@pytest.mark.asyncio
async def test_post_with_refresh_raises_without_return_code() -> None:
    """post_with_refresh raises when API lacks a return code."""

    resp = _FakeResp(200, "{}")
    session = MagicMock()
    session.post.return_value = _CM(resp)

    api = KippyApi(session)
    api.cache_authentication(
        {"token": 1, "app_code": "1", "app_verification_code": "2"},
        credentials=("e", "p"),
    )

    with pytest.raises(ClientResponseError):
        await api.post_with_refresh("/x", {"a": 1}, REQUEST_HEADERS)


def test_helper_functions_cover_edge_cases() -> None:
    """Exercise helper utilities with bad inputs."""

    assert _redact({"list": [{"petID": 1}]}) == {"list": [{"petID": "***"}]}
    assert _decode_json("not json") is None
    assert _get_return_code({"return": "5"}) == 5
    assert _get_return_code({"Result": "5"}) == 5
    assert _get_return_code(123) is None
    assert _get_return_code({"return": True}) is True
    assert _return_code_error(RETURN_VALUES.INVALID_CREDENTIALS).startswith("Invalid")
    assert _treat_401_as_success("/", {"return": False}) is False
    assert _treat_401_as_success("/", {}) is False
    start = datetime(2020, 1, 1)
    end = datetime(2020, 1, 8)
    weeks = _weeks_param(start, end)
    assert '"year": "2020"' in weeks
    assert _tz_hours(datetime.now(timezone.utc)) == 0
    assert _redact_json('{"petID":1}') == '{"petID": "***"}'


def test_ensure_login_raises_without_creds() -> None:
    """ensure_login raises when credentials have not been cached."""

    api = KippyApi(MagicMock())
    with pytest.raises(RuntimeError):
        asyncio.get_event_loop().run_until_complete(api.ensure_login())


@pytest.mark.asyncio
async def test_get_pet_kippy_list_maps_enable_gps(monkeypatch) -> None:
    """enableGPSOnDefault is mapped to gpsOnDefault."""

    api = KippyApi(MagicMock())
    api.cache_authentication({"app_code": "1", "app_verification_code": "2"})
    api.ensure_login = AsyncMock()  # type: ignore[assignment]

    async def fake_post(_path, _payload, _headers):
        return {
            "data": [
                {"petID": 1, "enableGPSOnDefault": True},
                {"petID": 2, "enableGPSOnDefault": False},
            ]
        }

    monkeypatch.setattr(
        api,
        "post_with_refresh",
        AsyncMock(side_effect=fake_post),
    )

    pets = await api.get_pet_kippy_list()
    assert pets[0]["gpsOnDefault"] == 1
    assert pets[1]["gpsOnDefault"] == 0


@pytest.mark.asyncio
async def test_get_pet_kippy_list_without_enable_gps(monkeypatch) -> None:
    """Pets lacking enableGPSOnDefault remain unchanged."""

    api = KippyApi(MagicMock())
    api.cache_authentication({"app_code": "1", "app_verification_code": "2"})
    api.ensure_login = AsyncMock()  # type: ignore[assignment]

    async def fake_post(_path, _payload, _headers):
        return {"data": [{"petID": 3}]}

    monkeypatch.setattr(
        api,
        "post_with_refresh",
        AsyncMock(side_effect=fake_post),
    )

    pets = await api.get_pet_kippy_list()
    assert "gpsOnDefault" not in pets[0]


@pytest.mark.asyncio
async def test_modify_kippy_settings_calls_post(monkeypatch) -> None:
    """modify_kippy_settings posts expected payload."""

    api = KippyApi(MagicMock())
    api.cache_authentication({"app_code": "1", "app_verification_code": "2"})
    api.ensure_login = AsyncMock()  # type: ignore[assignment]

    async def fake_post(path, payload, _headers):
        assert path == "/v2/kippymap_modifyKippySettings.php"
        assert payload["modify_kippy_id"] == 5
        assert payload["update_frequency"] == 2.0
        assert payload["app_code"] == "1"
        assert payload["app_verification_code"] == "2"
        return {"ok": True}

    monkeypatch.setattr(
        api,
        "post_with_refresh",
        AsyncMock(side_effect=fake_post),
    )

    result = await api.modify_kippy_settings(5, update_frequency=2)
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_modify_kippy_settings_propagates_error() -> None:
    """Exceptions from post_with_refresh are raised."""

    api = KippyApi(MagicMock())
    api.cache_authentication({"app_code": "1", "app_verification_code": "2"})
    api.ensure_login = AsyncMock()  # type: ignore[assignment]
    api.post_with_refresh = AsyncMock(
        side_effect=RuntimeError,
    )  # type: ignore[assignment]

    with pytest.raises(RuntimeError):
        await api.modify_kippy_settings(1, gps_on_default=True)


@pytest.mark.asyncio
async def test_modify_kippy_settings_uses_bools(monkeypatch) -> None:
    """gps_on_default is sent as boolean values."""

    api = KippyApi(MagicMock())
    api.cache_authentication({"app_code": "1", "app_verification_code": "2"})
    api.ensure_login = AsyncMock()  # type: ignore[assignment]

    payloads: list[dict[str, Any]] = []

    async def fake_post(_path, payload, _headers):
        payloads.append(payload)
        return {}

    monkeypatch.setattr(
        api,
        "post_with_refresh",
        AsyncMock(side_effect=fake_post),
    )

    await api.modify_kippy_settings(1, gps_on_default=True)
    await api.modify_kippy_settings(1, gps_on_default=False)

    assert payloads[0]["gps_on_default"] is True
    assert payloads[1]["gps_on_default"] is False


@pytest.mark.asyncio
async def test_post_with_refresh_logs_json(caplog) -> None:
    """Payloads are logged as JSON with lowercase booleans."""

    resp = _FakeResp(200, '{"return": 0}')
    session = MagicMock()
    session.post.return_value = _CM(resp)

    api = KippyApi(session)
    api.cache_authentication({"token": 1})

    caplog.set_level(logging.DEBUG, logger="custom_components.kippy.api")

    await api.post_with_refresh("/x", {"gps_on_default": True}, REQUEST_HEADERS)

    assert '"gps_on_default": true' in caplog.text
