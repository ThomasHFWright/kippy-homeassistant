import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.kippy import async_setup_entry, async_unload_entry
from custom_components.kippy.const import DOMAIN, PLATFORMS


@pytest.mark.asyncio
async def test_async_setup_entry_missing_credentials() -> None:
    """Setup fails when credentials are missing."""
    hass = MagicMock()
    hass.data = {}
    entry = MagicMock()
    entry.entry_id = "1"
    entry.data = {}
    result = await async_setup_entry(hass, entry)
    assert result is False


@pytest.mark.asyncio
async def test_async_setup_entry_login_failure() -> None:
    """Login exceptions raise ConfigEntryNotReady."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    entry = MagicMock()
    entry.entry_id = "1"
    entry.data = {CONF_EMAIL: "a", CONF_PASSWORD: "b"}
    api = AsyncMock()
    api.login.side_effect = Exception
    with patch("custom_components.kippy.aiohttp_client.async_get_clientsession"), patch(
        "custom_components.kippy.KippyApi.async_create", return_value=api
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_async_setup_entry_success_and_unload() -> None:
    """Successful setup stores data and unload removes it."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    entry = MagicMock()
    entry.entry_id = "1"
    entry.data = {CONF_EMAIL: "a", CONF_PASSWORD: "b"}

    api = AsyncMock()
    api.login = AsyncMock()
    data_coord = AsyncMock()
    data_coord.async_config_entry_first_refresh = AsyncMock()
    data_coord.data = {"pets": [{"petID": 1, "kippyID": 1}]}
    map_coord = AsyncMock()
    map_coord.async_config_entry_first_refresh = AsyncMock()
    activity_coord = AsyncMock()
    activity_coord.async_config_entry_first_refresh = AsyncMock()

    with patch("custom_components.kippy.aiohttp_client.async_get_clientsession"), patch(
        "custom_components.kippy.KippyApi.async_create", return_value=api
    ), patch(
        "custom_components.kippy.KippyDataUpdateCoordinator", return_value=data_coord
    ), patch(
        "custom_components.kippy.KippyMapDataUpdateCoordinator", return_value=map_coord
    ), patch(
        "custom_components.kippy.KippyActivityCategoriesDataUpdateCoordinator",
        return_value=activity_coord,
    ):
        result = await async_setup_entry(hass, entry)
    assert result is True
    assert DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]
    await async_unload_entry(hass, entry)
    hass.config_entries.async_unload_platforms.assert_awaited_with(entry, PLATFORMS)
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.asyncio
async def test_async_setup_entry_skips_expired_pet() -> None:
    """Expired pets are not set up for map or activity coordinators."""
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    entry = MagicMock()
    entry.entry_id = "1"
    entry.data = {CONF_EMAIL: "a", CONF_PASSWORD: "b"}

    api = AsyncMock()
    api.login = AsyncMock()
    data_coord = AsyncMock()
    data_coord.async_config_entry_first_refresh = AsyncMock()
    data_coord.data = {
        "pets": [
            {"petID": 1, "kippyID": 1, "expired_days": -1},
            {"petID": 2, "kippyID": 2, "expired_days": 0},
        ]
    }
    map_coord = AsyncMock()
    map_coord.async_config_entry_first_refresh = AsyncMock()
    activity_coord = AsyncMock()
    activity_coord.async_config_entry_first_refresh = AsyncMock()

    with patch("custom_components.kippy.aiohttp_client.async_get_clientsession"), patch(
        "custom_components.kippy.KippyApi.async_create", return_value=api
    ), patch(
        "custom_components.kippy.KippyDataUpdateCoordinator", return_value=data_coord
    ), patch(
        "custom_components.kippy.KippyMapDataUpdateCoordinator", return_value=map_coord
    ) as map_cls, patch(
        "custom_components.kippy.KippyActivityCategoriesDataUpdateCoordinator",
        return_value=activity_coord,
    ) as act_cls:
        result = await async_setup_entry(hass, entry)

    assert result is True
    map_cls.assert_called_once_with(hass, entry, api, 1)
    act_cls.assert_called_once_with(hass, entry, api, [1])
