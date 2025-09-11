import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kippy import async_setup_entry, async_unload_entry
from custom_components.kippy.const import DOMAIN, PLATFORMS


@pytest.mark.asyncio
async def test_async_setup_entry_missing_credentials(hass: HomeAssistant) -> None:
    """Setup fails when credentials are missing."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="1")
    with patch("custom_components.kippy.aiohttp_client.async_get_clientsession") as get_session:
        result = await async_setup_entry(hass, entry)
    assert result is False
    get_session.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_entry_login_failure(hass: HomeAssistant) -> None:
    """Login exceptions raise ConfigEntryNotReady."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_EMAIL: "a", CONF_PASSWORD: "b"}, entry_id="1"
    )
    entry.add_to_hass(hass)
    api = AsyncMock()
    api.login.side_effect = Exception
    with patch("custom_components.kippy.aiohttp_client.async_get_clientsession"), patch(
        "custom_components.kippy.KippyApi.async_create", return_value=api
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups", AsyncMock()
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_async_setup_entry_success_and_unload(hass: HomeAssistant) -> None:
    """Successful setup stores data and unload removes it."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_EMAIL: "a", CONF_PASSWORD: "b"}, entry_id="1"
    )
    entry.add_to_hass(hass)

    api = AsyncMock()
    api.login = AsyncMock()
    data_coord = AsyncMock()
    data_coord.async_config_entry_first_refresh = AsyncMock()
    data_coord.data = {"pets": [{"petID": 1, "kippyID": 1}]}
    map_coord = AsyncMock()
    map_coord.async_config_entry_first_refresh = AsyncMock()
    activity_coord = AsyncMock()
    activity_coord.async_config_entry_first_refresh = AsyncMock()
    forward = AsyncMock()
    unload = AsyncMock(return_value=True)

    with patch("custom_components.kippy.aiohttp_client.async_get_clientsession"), patch(
        "custom_components.kippy.KippyApi.async_create", return_value=api
    ), patch(
        "custom_components.kippy.KippyDataUpdateCoordinator", return_value=data_coord
    ), patch(
        "custom_components.kippy.KippyMapDataUpdateCoordinator", return_value=map_coord
    ), patch(
        "custom_components.kippy.KippyActivityCategoriesDataUpdateCoordinator",
        return_value=activity_coord,
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups", forward
    ), patch.object(
        hass.config_entries, "async_unload_platforms", unload
    ):
        result = await async_setup_entry(hass, entry)
        assert result is True
        assert DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]
        await async_unload_entry(hass, entry)
        unload.assert_awaited_with(entry, PLATFORMS)
        assert entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.asyncio
async def test_async_setup_entry_handles_expired_pet(hass: HomeAssistant) -> None:
    """Expired pets are excluded from map and activity coordinators but remain in data."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_EMAIL: "a", CONF_PASSWORD: "b"}, entry_id="1"
    )
    entry.add_to_hass(hass)

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
    forward = AsyncMock()

    with patch("custom_components.kippy.aiohttp_client.async_get_clientsession"), patch(
        "custom_components.kippy.KippyApi.async_create", return_value=api
    ), patch(
        "custom_components.kippy.KippyDataUpdateCoordinator", return_value=data_coord
    ), patch(
        "custom_components.kippy.KippyMapDataUpdateCoordinator", return_value=map_coord
    ) as map_cls, patch(
        "custom_components.kippy.KippyActivityCategoriesDataUpdateCoordinator",
        return_value=activity_coord,
    ) as act_cls, patch.object(
        hass.config_entries, "async_forward_entry_setups", forward
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    map_cls.assert_called_once_with(hass, entry, api, 1)
    act_cls.assert_called_once_with(hass, entry, api, [1])


@pytest.mark.asyncio
async def test_activity_refresh_also_refreshes_map(hass: HomeAssistant) -> None:
    """Scheduled activity refresh also requests map refresh."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_EMAIL: "a", CONF_PASSWORD: "b"}, entry_id="1"
    )
    entry.add_to_hass(hass)

    api = AsyncMock()
    api.login = AsyncMock()
    data_coord = AsyncMock()
    data_coord.async_config_entry_first_refresh = AsyncMock()
    data_coord.data = {"pets": [{"petID": 1, "kippyID": 1, "updateFrequency": "0"}]}
    data_coord.async_add_listener = MagicMock()
    map_coord = AsyncMock()
    map_coord.async_config_entry_first_refresh = AsyncMock()
    map_coord.data = {"contact_time": "0"}
    map_coord.async_request_refresh = AsyncMock()
    map_coord.async_add_listener = MagicMock()
    map_coord.set_activity_refresh_scheduler = MagicMock()
    map_coord.activity_refresh_delay = 0
    activity_coord = AsyncMock()
    activity_coord.async_config_entry_first_refresh = AsyncMock()
    activity_coord.async_refresh_pet = AsyncMock()
    forward = AsyncMock()

    def immediate_call_later(hass, delay, action):
        action(None)
        return lambda: None

    with patch(
        "custom_components.kippy.aiohttp_client.async_get_clientsession"
    ), patch(
        "custom_components.kippy.KippyApi.async_create", return_value=api
    ), patch(
        "custom_components.kippy.KippyDataUpdateCoordinator", return_value=data_coord
    ), patch(
        "custom_components.kippy.KippyMapDataUpdateCoordinator", return_value=map_coord
    ), patch(
        "custom_components.kippy.KippyActivityCategoriesDataUpdateCoordinator",
        return_value=activity_coord,
    ), patch(
        "custom_components.kippy.async_call_later", side_effect=immediate_call_later
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups", forward
    ), patch.object(hass, "async_create_task", MagicMock()):
        assert await async_setup_entry(hass, entry) is True

    map_coord.async_request_refresh.assert_called_once()
    activity_coord.async_refresh_pet.assert_called_once_with(1)
