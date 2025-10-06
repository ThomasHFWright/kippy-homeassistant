"""Tests for the Kippy config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError, ClientResponseError
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kippy.config_flow import KippyConfigFlow
from custom_components.kippy.const import DEFAULT_DEVICE_UPDATE_INTERVAL_MINUTES, DOMAIN
from custom_components.kippy.helpers import DEVICE_UPDATE_INTERVAL_KEY


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


@pytest.mark.asyncio
async def test_options_flow_success(hass: HomeAssistant) -> None:
    """Options flow stores the configured update interval."""

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = KippyConfigFlow.async_get_options_flow(entry)
    assert flow is not None
    flow.hass = hass
    result = await flow.async_step_init()
    assert result["type"].value == "form"
    required_field = next(iter(result["data_schema"].schema))
    assert required_field.schema == DEVICE_UPDATE_INTERVAL_KEY
    assert callable(required_field.default)
    assert required_field.default() == str(DEFAULT_DEVICE_UPDATE_INTERVAL_MINUTES)

    result = await flow.async_step_init({DEVICE_UPDATE_INTERVAL_KEY: "30"})
    assert result["type"].value == "create_entry"
    assert result["data"][DEVICE_UPDATE_INTERVAL_KEY] == 30


@pytest.mark.asyncio
async def test_options_flow_validates_interval(hass: HomeAssistant) -> None:
    """Invalid intervals return the form with an error."""

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = KippyConfigFlow.async_get_options_flow(entry)
    flow.hass = hass

    result = await flow.async_step_init({DEVICE_UPDATE_INTERVAL_KEY: "0"})
    assert result["type"].value == "form"
    assert result["errors"]["base"] == "invalid_device_update_interval"

    result = await flow.async_step_init({DEVICE_UPDATE_INTERVAL_KEY: "abc"})
    assert result["type"].value == "form"
    assert result["errors"]["base"] == "invalid_device_update_interval"
