"""Tests for the in-memory fake Kippy API."""

from __future__ import annotations

import pytest
import pytest_asyncio


class _FakeKippyApi:
    """Fallback API used when no credentials are provided."""

    is_fake = True
    app_code = "FAKE_CODE"
    app_verification_code = "FAKE_VERIFICATION_CODE"

    async def get_pet_kippy_list(self) -> list:
        return [
            {
                "petID": "12345",
                "kippyID": "234",
                "name": "Fido",
                "petKind": "4",
                "expired_days": -1,
            },
            {
                "petID": "54321",
                "kippyID": "432",
                "name": "Fluffy",
                "petKind": "3",
                "expired_days": 0,
            },
        ]

    async def kippymap_action(self, *args, **kwargs) -> dict:  # noqa: D401
        return {"fake": True}

    async def get_activity_categories(self, *args, **kwargs) -> dict:
        return {"fake": True}


@pytest_asyncio.fixture
async def api():
    """Return the fake API instance."""

    return _FakeKippyApi()


@pytest.mark.asyncio
async def test_login_succeeds(api) -> None:
    """Ensure the fake API exposes expected codes."""

    assert api.app_code == "FAKE_CODE"
    assert api.app_verification_code == "FAKE_VERIFICATION_CODE"


@pytest.mark.asyncio
async def test_get_pet_kippy_list_returns_list(api) -> None:
    """The fake API returns the expected pets."""

    pets = await api.get_pet_kippy_list()
    assert isinstance(pets, list)
    assert any(
        pet["name"] == "Fido"
        and pet["petID"] == "12345"
        and pet["kippyID"] == "234"
        and pet["petKind"] == "4"
        and pet["expired_days"] == -1
        for pet in pets
    )
    assert any(
        pet["name"] == "Fluffy"
        and pet["petID"] == "54321"
        and pet["kippyID"] == "432"
        and pet["petKind"] == "3"
        and pet["expired_days"] == 0
        for pet in pets
    )


@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories(api) -> None:
    """The fake API returns placeholder data for map and activity endpoints."""

    location = await api.kippymap_action(12345)
    activity = await api.get_activity_categories(12345, "", "", 0, 0)
    assert location == {"fake": True}
    assert activity == {"fake": True}


@pytest.mark.asyncio
async def test_fake_api_flag(api) -> None:
    """Ensure the fake API advertises itself."""

    assert api.is_fake is True


@pytest.mark.asyncio
async def test_fake_pet_active_subscription(api) -> None:
    """Ensure the fake API exposes an active pet."""

    pets = await api.get_pet_kippy_list()
    assert any(int(p["expired_days"]) < 0 for p in pets)


@pytest.mark.asyncio
async def test_fake_pet_inactive_subscription(api) -> None:
    """Ensure the fake API exposes an inactive pet."""

    pets = await api.get_pet_kippy_list()
    assert any(int(p["expired_days"]) >= 0 for p in pets)
