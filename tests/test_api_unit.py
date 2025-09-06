from __future__ import annotations

import asyncio
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
        return self.resp

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeResp:
    def __init__(self, status: int, text: str = "{}"):
        self.status = status
        self._text = text
        self.headers = {}
        self.request_info = MagicMock()
        self.history: tuple = ()

    async def text(self) -> str:  # noqa: D401
        return self._text

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise ClientResponseError(
                self.request_info,
                self.history,
                status=self.status,
                message="err",
                headers={},
            )


@pytest.mark.asyncio
async def test_login_handles_return_code_failure(monkeypatch) -> None:
    """Login raises for unsuccessful return codes."""

    resp = _FakeResp(200, '{"return": 108}')
    session = MagicMock()
    session.post.return_value = _CM(resp)

    api = KippyApi(session)
    with pytest.raises(ClientResponseError):
        await api.login("a", "b", force=True)


@pytest.mark.asyncio
async def test_post_with_refresh_retries_on_expired(monkeypatch) -> None:
    """_post_with_refresh refreshes login once then returns data."""

    resp1 = _FakeResp(401, '{"return": %d}' % RETURN_VALUES.AUTHORIZATION_EXPIRED)
    resp2 = _FakeResp(200, '{"return": 0, "data": {"ok": true}}')
    session = MagicMock()
    session.post.side_effect = [_CM(resp1), _CM(resp2)]

    api = KippyApi(session)
    api._auth = {"token": 1, "app_code": "1", "app_verification_code": "2"}
    api._credentials = ("e", "p")

    async def fake_login(email, password, force=False):
        return {"app_code": "1", "app_verification_code": "2"}

    api.login = AsyncMock(side_effect=fake_login)  # type: ignore[assignment]

    result = await api._post_with_refresh("/x", {"a": 1}, REQUEST_HEADERS)
    assert result["data"]["ok"] is True


@pytest.mark.asyncio
async def test_post_with_refresh_raises_without_return_code() -> None:
    """_post_with_refresh raises when API lacks a return code."""

    resp = _FakeResp(200, "{}")
    session = MagicMock()
    session.post.return_value = _CM(resp)

    api = KippyApi(session)
    api._auth = {"token": 1, "app_code": "1", "app_verification_code": "2"}
    api._credentials = ("e", "p")

    with pytest.raises(ClientResponseError):
        await api._post_with_refresh("/x", {"a": 1}, REQUEST_HEADERS)


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
    api = KippyApi(MagicMock())
    with pytest.raises(RuntimeError):
        asyncio.get_event_loop().run_until_complete(api.ensure_login())


@pytest.mark.asyncio
async def test_modify_kippy_settings_calls_post(monkeypatch) -> None:
    """modify_kippy_settings posts expected payload."""

    api = KippyApi(MagicMock())
    api._auth = {"app_code": "1", "app_verification_code": "2"}
    api.ensure_login = AsyncMock()  # type: ignore[assignment]

    async def fake_post(path, payload, headers):
        assert path == "/v2/kippymap_modifyKippySettings.php"
        assert payload["modify_kippy_id"] == 5
        assert payload["update_frequency"] == 2.0
        assert payload["app_code"] == "1"
        assert payload["app_verification_code"] == "2"
        return {"ok": True}

    monkeypatch.setattr(api, "_post_with_refresh", AsyncMock(side_effect=fake_post))

    result = await api.modify_kippy_settings(5, update_frequency=2)
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_modify_kippy_settings_propagates_error() -> None:
    """Exceptions from _post_with_refresh are raised."""

    api = KippyApi(MagicMock())
    api._auth = {"app_code": "1", "app_verification_code": "2"}
    api.ensure_login = AsyncMock()  # type: ignore[assignment]
    api._post_with_refresh = AsyncMock(side_effect=RuntimeError)

    with pytest.raises(RuntimeError):
        await api.modify_kippy_settings(1, gps_on_default=True)


@pytest.mark.asyncio
async def test_modify_kippy_settings_lowercase_bools(monkeypatch) -> None:
    """gps_on_default is sent as lowercase booleans."""

    api = KippyApi(MagicMock())
    api._auth = {"app_code": "1", "app_verification_code": "2"}
    api.ensure_login = AsyncMock()  # type: ignore[assignment]

    payloads: list[dict[str, Any]] = []

    async def fake_post(path, payload, headers):
        payloads.append(payload)
        return {}

    monkeypatch.setattr(api, "_post_with_refresh", AsyncMock(side_effect=fake_post))

    await api.modify_kippy_settings(1, gps_on_default=True)
    await api.modify_kippy_settings(1, gps_on_default=False)

    assert payloads[0]["gps_on_default"] == "true"
    assert payloads[1]["gps_on_default"] == "false"
