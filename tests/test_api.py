import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import pytest
from dotenv import load_dotenv

SECRETS_FILE = Path(__file__).resolve().parents[1] / ".secrets" / "kippy.env"

if SECRETS_FILE.exists():
    load_dotenv(SECRETS_FILE)
else:
    pytest.skip("Missing KIPPY secrets file", allow_module_level=True)

KIPPY_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "kippy"
custom_components = types.ModuleType("custom_components")
kippy_pkg = types.ModuleType("custom_components.kippy")
kippy_pkg.__path__ = [str(KIPPY_DIR)]
sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.kippy", kippy_pkg)

spec = importlib.util.spec_from_file_location(
    "custom_components.kippy.api", KIPPY_DIR / "api.py"
)
api_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_module)
KippyApi = api_module.KippyApi

EMAIL = os.getenv("KIPPY_EMAIL")
PASSWORD = os.getenv("KIPPY_PASSWORD")

if not EMAIL or not PASSWORD:
    pytest.fail("Missing KIPPY_EMAIL/KIPPY_PASSWORD secrets")


async def _create_api() -> KippyApi:
    session = aiohttp.ClientSession()
    api = await KippyApi.async_create(session)
    await api.login(EMAIL, PASSWORD, force=True)
    return api


@pytest.mark.asyncio
async def test_login_succeeds():
    api = await _create_api()
    try:
        assert api.app_code is not None
        assert api.app_verification_code is not None
    finally:
        await api._session.close()


@pytest.mark.asyncio
async def test_get_pet_kippy_list_returns_list():
    api = await _create_api()
    try:
        pets = await api.get_pet_kippy_list()
        assert isinstance(pets, list)
    finally:
        await api._session.close()


@pytest.mark.asyncio
async def test_kippymap_action_and_activity_categories():
    api = await _create_api()
    try:
        pets = await api.get_pet_kippy_list()
        if not pets:
            pytest.skip("No pets available for account")
        pet = pets[0]
        kippy_id = (
            pet.get("kippy_id")
            or pet.get("device_kippy_id")
            or pet.get("deviceID")
            or pet.get("deviceId")
        )
        if kippy_id:
            location = await api.kippymap_action(int(kippy_id), do_sms=False)
            assert isinstance(location, dict)
        pet_id = pet.get("petID") or pet.get("id")
        if pet_id:
            today = datetime.utcnow().date()
            from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
            activity = await api.get_activity_categories(
                int(pet_id), from_date, to_date, 1, 1
            )
            assert isinstance(activity, dict)
    finally:
        await api._session.close()
