"""Opt-in, read-only checks against Kippy's real service.

Run with KIPPY_LIVE_TESTS=1 and credentials in .secrets/kippy.env or the
process environment. Authentication and connection failures fail the check.
"""

import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import aiohttp
import pytest
from dotenv import load_dotenv
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from kippy_api import KippyApi
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_socket import socket_allow_hosts

from custom_components.kippy.const import DOMAIN

pytestmark = [pytest.mark.live, pytest.mark.enable_socket, pytest.mark.asyncio]
_REAL_GETADDRINFO = socket.getaddrinfo


@pytest.fixture(autouse=True)
def live_network(monkeypatch, socket_enabled):
    """Allow only the vendor and localhost after HA installs its socket guard."""
    if os.getenv("KIPPY_LIVE_TESTS") != "1":
        pytest.skip("Set KIPPY_LIVE_TESTS=1 to enable live checks")
    load_dotenv(Path(__file__).resolve().parents[1] / ".secrets" / "kippy.env")
    if not os.getenv("KIPPY_EMAIL") or not os.getenv("KIPPY_PASSWORD"):
        pytest.skip("Populate KIPPY_EMAIL and KIPPY_PASSWORD for live checks")
    monkeypatch.setattr(socket, "getaddrinfo", _REAL_GETADDRINFO)
    socket_allow_hosts(["prod.kippyapi.eu", "127.0.0.1"], allow_unix_socket=True)
    try:
        yield
    finally:
        socket_allow_hosts(["127.0.0.1"], allow_unix_socket=True)


async def test_live_read_only() -> None:
    """Authenticate and read every active pet without sending device commands."""
    if os.getenv("KIPPY_LIVE_TESTS") != "1":
        pytest.skip("Set KIPPY_LIVE_TESTS=1 to enable live checks")
    load_dotenv(Path(__file__).resolve().parents[1] / ".secrets" / "kippy.env")
    email = os.getenv("KIPPY_EMAIL")
    password = os.getenv("KIPPY_PASSWORD")
    if not email or not password:
        pytest.skip("Populate KIPPY_EMAIL and KIPPY_PASSWORD for live checks")

    async with aiohttp.ClientSession() as session:
        api = await KippyApi.async_create(session)
        await api.login(email, password)
        assert api.app_code is not None
        assert api.app_verification_code is not None
        pets = await api.get_pet_kippy_list()
        assert isinstance(pets, list)
        today = datetime.now(timezone.utc).date()
        for pet in pets:
            days = pet.get("expired_days")
            if days is not None and int(days) >= 0:
                continue
            pet_id = pet.get("petID")
            kippy_id = pet.get("kippyID")
            if pet_id is None or kippy_id is None:
                continue
            location = await api.kippymap_action(int(kippy_id), do_sms=False)
            assert isinstance(location, dict)
            activity = await api.get_activity_categories(
                int(pet_id),
                (today - timedelta(days=7)).isoformat(),
                today.isoformat(),
                2,
                1,
                timezone=timezone.utc,
            )
            assert isinstance(activity, dict)


async def test_live_home_assistant_lifecycle(
    hass, entity_registry, device_registry, disable_mock_zeroconf_resolver
):
    """Load real pets through HA using cached map reads, then unload cleanly."""
    if os.getenv("KIPPY_LIVE_TESTS") != "1":
        pytest.skip("Set KIPPY_LIVE_TESTS=1 to enable live checks")
    load_dotenv(Path(__file__).resolve().parents[1] / ".secrets" / "kippy.env")
    email = os.getenv("KIPPY_EMAIL")
    password = os.getenv("KIPPY_PASSWORD")
    if not email or not password:
        pytest.skip("Populate KIPPY_EMAIL and KIPPY_PASSWORD for live checks")

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=email,
        data={CONF_EMAIL: email, CONF_PASSWORD: password},
    )
    entry.add_to_hass(hass)
    session = async_get_clientsession(hass)
    original_map = KippyApi.kippymap_action

    async def cached_map(api, *args, **kwargs):
        """Read cached coordinates without requesting a device refresh."""
        kwargs["do_sms"] = False
        return await original_map(api, *args, **kwargs)

    # HA registry logs contain real pet names; keep account data out of output.
    logging_disabled = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with patch.object(KippyApi, "kippymap_action", cached_map):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
            devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
            entities = er.async_entries_for_config_entry(
                entity_registry, entry.entry_id
            )
            assert len(devices) > 0, "No devices were registered"
            assert len(entities) > 0, "No entities were registered"
            trackers = [
                entity for entity in entities if entity.domain == "device_tracker"
            ]
            assert len(trackers) > 0, "No active pet trackers were registered"
            device_ids = {device.id for device in devices}
            for tracker in trackers:
                assert tracker.device_id in device_ids, (
                    "Tracker has no linked pet device"
                )
                state = hass.states.get(tracker.entity_id)
                assert state is not None, "Tracker state was not created"
                assert state.state != "unavailable", "Tracker is unavailable"
            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert not session.closed, (
                "Integration closed Home Assistant's shared session"
            )
    finally:
        if entry.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
        logging.disable(logging_disabled)
