"""Integration tests for the real Kippy API.

These tests require valid credentials defined in environment variables or the
``.secrets/kippy.env`` file. When credentials are missing or use placeholder
values like ``"<REDACTED>"``, the tests are skipped. Tests for the in-memory
fake API live in ``test_api_fake.py``.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiohttp
import pytest
import pytest_asyncio
from dotenv import load_dotenv

from custom_components.kippy.api import KippyApi
from custom_components.kippy.const import MISSING_CREDENTIAL_PLACEHOLDERS

SECRETS_FILE = Path(__file__).resolve().parents[1] / ".secrets" / "kippy.env"

if SECRETS_FILE.exists():
    load_dotenv(SECRETS_FILE)

EMAIL = os.getenv("KIPPY_EMAIL")
PASSWORD = os.getenv("KIPPY_PASSWORD")

if (
    not EMAIL
    or not PASSWORD
    or any(value in MISSING_CREDENTIAL_PLACEHOLDERS for value in (EMAIL, PASSWORD))
):
    pytest.skip(
        "Kippy credentials are missing or redacted; skipping real API tests",
        allow_module_level=True,
    )


def _active(pet: dict[str, Any]) -> bool:
    """Return True if the subscription is active for the given pet."""

    days = pet.get("expired_days")
    try:
        return int(days) < 0
    except (TypeError, ValueError):
        return True


@pytest_asyncio.fixture
async def api():
    """Return an authenticated Kippy API instance."""

    session = aiohttp.ClientSession()
    api = await KippyApi.async_create(session)
    await api.login(EMAIL, PASSWORD, force=True)
    try:
        yield api
    finally:
        await api._session.close()


@pytest.mark.asyncio
async def test_login_succeeds(api) -> None:
    """Ensure login provides the expected codes."""

    assert api.app_code is not None
    assert api.app_verification_code is not None


@pytest.mark.asyncio
async def test_get_pet_kippy_list_returns_list(api) -> None:
    """The pet list should always be a list."""

    pets = await api.get_pet_kippy_list()
    assert isinstance(pets, list)



@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories(api) -> None:
    """Exercise Kippy Map and activity endpoints when possible."""

    pets = await api.get_pet_kippy_list()

    if not pets:
        pytest.skip("No pets returned; skipping location and activity tests")

    pet = next(
        (
            p
            for p in pets
            if _active(p)
            and (
                (p.get("kippy_id")
                or p.get("kippyID")
                or p.get("device_kippy_id")
                or p.get("deviceID")
                or p.get("deviceId"))
                and (p.get("petID") or p.get("id"))
            )
        ),
        None,
    )
    if pet is None:
        pytest.skip(
            "No pet with kippy_id, pet_id and active subscription; skipping location and activity tests",
        )

    kippy_id = (
        pet.get("kippy_id")
        or pet.get("kippyID")
        or pet.get("device_kippy_id")
        or pet.get("deviceID")
        or pet.get("deviceId")
    )
    location = await api.kippymap_action(int(kippy_id), do_sms=False)
    assert isinstance(location, dict)

    pet_id = pet.get("petID") or pet.get("id")
    today = datetime.now(timezone.utc).date()
    from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    activity = await api.get_activity_categories(int(pet_id), from_date, to_date, 1, 1)
    assert isinstance(activity, dict)

@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories_inactive_subscription(api) -> None:
    """Exercise endpoints for a pet with an inactive subscription."""

    pets = await api.get_pet_kippy_list()

    inactive = next(
        (
            p
            for p in pets
            if not _active(p)
            and (
                (p.get("kippy_id")
                or p.get("kippyID")
                or p.get("device_kippy_id")
                or p.get("deviceID")
                or p.get("deviceId"))
                and (p.get("petID") or p.get("id"))
            )
        ),
        None,
    )

    if inactive is None:
        pytest.skip("No pet with inactive subscription; skipping location test")

    kippy_id = (
        inactive.get("kippy_id")
        or inactive.get("kippyID")
        or inactive.get("device_kippy_id")
        or inactive.get("deviceID")
        or inactive.get("deviceId")
    )
    location = await api.kippymap_action(int(kippy_id), do_sms=False)
    assert isinstance(location, dict)

    pet_id = inactive.get("petID") or inactive.get("id")
    today = datetime.now(timezone.utc).date()
    from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    activity = await api.get_activity_categories(int(pet_id), from_date, to_date, 1, 1)
    assert isinstance(activity, dict)

@pytest.mark.asyncio
async def test_kippymap_action_handles_inactive_subscription(monkeypatch) -> None:
    """kippymap_action should surface subscription status."""

    session = aiohttp.ClientSession()
    api = await KippyApi.async_create(session)
    api._auth = {"token": 1}

    async def fake_post(path, payload, headers):
        return {"return": False}

    async def fake_ensure_login():
        return None

    monkeypatch.setattr(api, "_post_with_refresh", fake_post)
    monkeypatch.setattr(api, "ensure_login", fake_ensure_login)

    result = await api.kippymap_action(12345)
    await session.close()

    assert result == {"return": False}


@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories_no_pets(
    monkeypatch, api
) -> None:
    """The combined test skips when no pets are returned."""

    async def fake_get_pet_kippy_list():
        return []

    monkeypatch.setattr(api, "get_pet_kippy_list", fake_get_pet_kippy_list)

    with pytest.raises(pytest.skip.Exception):
        await test_kippymap_action_and_activity_categories(api)


@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories_active_subscription(
    monkeypatch, api
) -> None:
    """The combined test runs when subscription is active."""

    async def fake_get_pet_kippy_list():
        return [{"kippyID": "1", "petID": "1", "expired_days": -1}]

    called = {"map": 0, "activity": 0}

    async def fake_kippymap_action(*_args, **_kwargs):
        called["map"] += 1
        return {}

    async def fake_get_activity_categories(*_args, **_kwargs):
        called["activity"] += 1
        return {}

    monkeypatch.setattr(api, "get_pet_kippy_list", fake_get_pet_kippy_list)
    monkeypatch.setattr(api, "kippymap_action", fake_kippymap_action)
    monkeypatch.setattr(
        api, "get_activity_categories", fake_get_activity_categories
    )

    await test_kippymap_action_and_activity_categories(api)

    assert called["map"] == 1
    assert called["activity"] == 1


@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories_inactive_subscription_skips(
    monkeypatch, api
) -> None:
    """The combined test skips when subscription inactive."""

    async def fake_get_pet_kippy_list():
        return [{"kippyID": "1", "petID": "1", "expired_days": 0}]

    monkeypatch.setattr(api, "get_pet_kippy_list", fake_get_pet_kippy_list)

    with pytest.raises(pytest.skip.Exception):
        await test_kippymap_action_and_activity_categories(api)


@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories_no_kippy_id(
    monkeypatch, api
) -> None:
    """The combined test skips when pet lacks a kippy id."""

    async def fake_get_pet_kippy_list():
        return [{"petID": "123"}]

    monkeypatch.setattr(api, "get_pet_kippy_list", fake_get_pet_kippy_list)

    with pytest.raises(pytest.skip.Exception):
        await test_kippymap_action_and_activity_categories(api)


@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories_no_pet_id(
    monkeypatch, api
) -> None:
    """The combined test skips when pet lacks a pet id."""

    async def fake_get_pet_kippy_list():
        return [{"device_kippy_id": "456"}]

    async def fake_kippymap_action(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(api, "get_pet_kippy_list", fake_get_pet_kippy_list)
    monkeypatch.setattr(api, "kippymap_action", fake_kippymap_action)

    with pytest.raises(pytest.skip.Exception):
        await test_kippymap_action_and_activity_categories(api)
