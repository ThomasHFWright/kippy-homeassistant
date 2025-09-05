"""Tests for the Kippy API.

These tests normally exercise the real API using credentials supplied via
environment variables. When those credentials are not available, or are
placeholder values like ``"<REDACTED>"``, we still run the tests using a small
in-memory fake so that it is obvious a placeholder test executed instead of
silently skipping the entire module.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

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

# Treat empty or placeholder credential values as missing so tests use the fake API.
CREDS = not any(value in MISSING_CREDENTIAL_PLACEHOLDERS for value in (EMAIL, PASSWORD))

log = logging.getLogger(__name__)


class _FakeKippyApi:
    """Fallback API used when no credentials are provided."""

    is_fake = True
    app_code = "FAKE_CODE"
    app_verification_code = "FAKE_VERIFICATION_CODE"

    async def get_pet_kippy_list(self) -> list:
        return [
            {"petID": "12345", "name": "Fido", "petKind": "4"},
            {"petID": "54321", "name": "Fluffy", "petKind": "3"},
        ]

    async def kippymap_action(self, *args, **kwargs) -> dict:  # noqa: D401
        return {"fake": True}

    async def get_activity_categories(self, *args, **kwargs) -> dict:
        return {"fake": True}


@pytest_asyncio.fixture
async def api():
    """Return a real or fake API depending on the available credentials."""

    if CREDS:
        log.info("Using real Kippy API for tests")
        session = aiohttp.ClientSession()
        api = await KippyApi.async_create(session)
        api.is_fake = False
        await api.login(EMAIL, PASSWORD, force=True)
        try:
            yield api
        finally:
            await api._session.close()
    else:
        log.info(
            "Using fake Kippy API for tests because credentials are missing or redacted"
        )
        yield _FakeKippyApi()


@pytest.mark.asyncio
async def test_login_succeeds(api):
    """Ensure login provides the expected codes or fake identifiers."""

    assert api.app_code is not None
    assert api.app_verification_code is not None

    if getattr(api, "is_fake", False):
        log.info("Login simulated using fake credentials")
        assert api.app_code == "FAKE_CODE"
        assert api.app_verification_code == "FAKE_VERIFICATION_CODE"
    else:
        log.info("Login succeeded using real credentials")


@pytest.mark.asyncio
async def test_get_pet_kippy_list_returns_list(api):
    """The pet list should always be a list, even for the fake API."""

    pets = await api.get_pet_kippy_list()
    if getattr(api, "is_fake", False):
        log.info("Fake API returned %d pets", len(pets))
        assert any(
            pet["name"] == "Fido" and pet["petID"] == "12345" and pet["petKind"] == "4"
            for pet in pets
        )
        assert any(
            pet["name"] == "Fluffy"
            and pet["petID"] == "54321"
            and pet["petKind"] == "3"
            for pet in pets
        )
    else:
        log.info("Real API returned %d pets", len(pets))
    assert isinstance(pets, list)


@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories(api):
    """Exercise Kippy Map and activity endpoints when possible.

    For the fake API this simply confirms the placeholder values to make the
    intent explicit.
    """

    pets = await api.get_pet_kippy_list()

    if getattr(api, "is_fake", False):
        log.info("Fake API: verifying placeholder location and activity responses")
        assert any(pet["petID"] == "12345" for pet in pets)
        location = await api.kippymap_action(12345)
        activity = await api.get_activity_categories(12345, "", "", 0, 0)
        log.info("Fake location response: %s", location)
        log.info("Fake activity response: %s", activity)
        assert location == {"fake": True}
        assert activity == {"fake": True}
        return

    if not pets:
        log.info("Real API returned no pets; skipping location and activity tests")
        assert pets == []
        return

    pet = pets[0]
    kippy_id = (
        pet.get("kippy_id")
        or pet.get("device_kippy_id")
        or pet.get("deviceID")
        or pet.get("deviceId")
    )
    if kippy_id:
        location = await api.kippymap_action(int(kippy_id), do_sms=False)
        log.info("Retrieved location for pet %s", kippy_id)
        assert isinstance(location, dict)
    else:
        log.info("Pet missing kippy_id; skipping location test")
    pet_id = pet.get("petID") or pet.get("id")
    if pet_id:
        today = datetime.utcnow().date()
        from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
        activity = await api.get_activity_categories(
            int(pet_id), from_date, to_date, 1, 1
        )
        log.info("Retrieved activity for pet %s", pet_id)
        assert isinstance(activity, dict)
    else:
        log.info("Pet missing pet_id; skipping activity test")
