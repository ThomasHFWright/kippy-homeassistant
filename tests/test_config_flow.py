from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError, ClientResponseError
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kippy.const import (
    CONF_ACTIVITY_UPDATE_INTERVAL,
    DOMAIN,
)

from custom_components.kippy.config_flow import KippyConfigFlow


@pytest.mark.asyncio
async def test_config_flow_success() -> None:
    """Successful login creates an entry."""
    flow = KippyConfigFlow()
    flow.hass = MagicMock()
    with patch(
        "custom_components.kippy.config_flow.aiohttp_client.async_get_clientsession"
    ), patch("custom_components.kippy.config_flow.KippyApi.async_create") as create:
        api = AsyncMock()
        create.return_value = api
        api.login.return_value = None
        result = await flow.async_step_user({CONF_EMAIL: "user", CONF_PASSWORD: "pass"})
    assert result["type"].value == "create_entry"
    assert result["data"] == {CONF_EMAIL: "user", CONF_PASSWORD: "pass"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,base",
    [
        (ClientResponseError(MagicMock(), (), status=401, message=""), "invalid_auth"),
        (
            ClientResponseError(MagicMock(), (), status=500, message="boom"),
            "cannot_connect",
        ),
        (ClientError(), "cannot_connect"),
        (Exception(), "unknown"),
    ],
)
async def test_config_flow_errors(error: Exception, base: str) -> None:
    """Ensure different errors are handled."""
    flow = KippyConfigFlow()
    flow.hass = MagicMock()
    with patch(
        "custom_components.kippy.config_flow.aiohttp_client.async_get_clientsession"
    ), patch("custom_components.kippy.config_flow.KippyApi.async_create") as create:
        api = AsyncMock()
        create.return_value = api
        api.login.side_effect = error
        result = await flow.async_step_user({CONF_EMAIL: "user", CONF_PASSWORD: "pass"})
    assert result["type"].value == "form"
    assert result["errors"]["base"] == base


@pytest.mark.asyncio
async def test_options_flow(hass) -> None:
    """Options flow allows configuring activity update interval."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = KippyConfigFlow.async_get_options_flow(entry)
    flow.hass = hass

    result = await flow.async_step_init()
    assert result["type"].value == "form"

    result = await flow.async_step_init({CONF_ACTIVITY_UPDATE_INTERVAL: 20})
    assert result["type"].value == "create_entry"
    assert result["data"] == {CONF_ACTIVITY_UPDATE_INTERVAL: 20}
