"""Tests for the Kippy config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError, ClientResponseError
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.kippy.config_flow import KippyConfigFlow


@pytest.mark.asyncio
async def test_config_flow_success() -> None:
    """Successful login creates an entry."""
    flow = KippyConfigFlow()
    flow.hass = MagicMock()
    with (
        patch(
            "custom_components.kippy.config_flow.aiohttp_client.async_get_clientsession"
        ),
        patch("custom_components.kippy.config_flow.KippyApi.async_create") as create,
    ):
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
        (RuntimeError(), "unknown"),
        (Exception(), "unknown"),
    ],
)
async def test_config_flow_errors(error: Exception, base: str) -> None:
    """Ensure different errors are handled."""
    flow = KippyConfigFlow()
    flow.hass = MagicMock()
    with (
        patch(
            "custom_components.kippy.config_flow.aiohttp_client.async_get_clientsession"
        ),
        patch("custom_components.kippy.config_flow.KippyApi.async_create") as create,
    ):
        api = AsyncMock()
        create.return_value = api
        api.login.side_effect = error
        result = await flow.async_step_user({CONF_EMAIL: "user", CONF_PASSWORD: "pass"})
    assert result["type"].value == "form"
    assert result["errors"]["base"] == base


def test_config_flow_is_matching() -> None:
    """The flow matches other Kippy flows but not arbitrary ones."""

    flow = KippyConfigFlow()
    assert flow.is_matching(KippyConfigFlow())

    class DummyFlow(config_entries.ConfigFlow):
        """Config flow used to test non-matching flows."""

        VERSION = 1

        async def async_step_user(self, user_input=None):
            """Abort immediately to satisfy the abstract base."""
            return self.async_abort(reason="not_supported")

        def is_matching(self, other_flow: config_entries.ConfigFlow) -> bool:
            """Dummy flows never match other flows."""
            return False

    assert not flow.is_matching(DummyFlow())
