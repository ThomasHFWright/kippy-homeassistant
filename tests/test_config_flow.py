"""Tests for the Kippy config and reauthentication flows."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import selector
from kippy_api import KippyAuthError, KippyConnectionError, KippyResponseError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kippy.config_flow import KippyConfigFlow
from custom_components.kippy.const import (
    DEFAULT_DEVICE_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_DEVICE_UPDATE_INTERVAL_MINUTES,
    MIN_DEVICE_UPDATE_INTERVAL_MINUTES,
)
from custom_components.kippy.helpers import DEVICE_UPDATE_INTERVAL_KEY


@pytest.fixture(name="login_api")
def _login_api():
    """Mock only the external API boundary during config flows."""
    with patch("custom_components.kippy.config_flow.KippyApi.async_create") as create:
        api = AsyncMock()
        create.return_value = api
        yield api


@pytest.mark.asyncio
async def test_config_flow_success(hass: HomeAssistant, login_api) -> None:
    """Successful login creates one entry using the account identity."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.kippy.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: "user", CONF_PASSWORD: "pass"}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_EMAIL: "user", CONF_PASSWORD: "pass"}
    assert result["result"].unique_id == "user"
    login_api.login.assert_awaited_once_with("user", "pass")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,base",
    [
        (KippyAuthError("Rejected", status=401), "invalid_auth"),
        (KippyResponseError("Service error", status=500), "cannot_connect"),
        (KippyConnectionError("Offline"), "cannot_connect"),
        (RuntimeError(), "unknown"),
    ],
)
async def test_config_flow_errors(hass, login_api, error, base) -> None:
    """Service errors map to recoverable config flow errors."""
    login_api.login.side_effect = error
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_EMAIL: "user", CONF_PASSWORD: "pass"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": base}


@pytest.mark.asyncio
async def test_config_flow_duplicate(hass, login_api) -> None:
    """An existing account cannot be configured a second time."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="user", data={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_EMAIL: "user", CONF_PASSWORD: "pass"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    login_api.login.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,base",
    [
        (KippyAuthError("Rejected"), "invalid_auth"),
        (KippyConnectionError("Offline"), "cannot_connect"),
        (KippyResponseError("Bad response"), "cannot_connect"),
        (RuntimeError("Unexpected"), "unknown"),
    ],
)
async def test_reauthentication_preserves_entry(hass, login_api, error, base):
    """Reauthentication retries and changes only the existing password."""
    options = {
        DEVICE_UPDATE_INTERVAL_KEY: 30,
        "pet_settings": {"1": {"ignore_lbs": True}},
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="user",
        title="My pets",
        data={CONF_EMAIL: "user", CONF_PASSWORD: "old"},
        options=options,
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["step_id"] == "reauth_confirm"
    assert {key.schema for key in result["data_schema"].schema} == {CONF_PASSWORD}
    login_api.login.side_effect = error
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new"}
    )
    assert result["errors"] == {"base": base}
    assert entry.data[CONF_PASSWORD] == "old"

    login_api.login.side_effect = None
    with patch.object(
        hass.config_entries, "async_reload", return_value=True
    ) as reload_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new"}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    reload_entry.assert_awaited_once_with(entry.entry_id)
    login_api.login.assert_awaited_with("user", "new")
    assert entry.unique_id == "user"
    assert entry.title == "My pets"
    assert entry.data == {CONF_EMAIL: "user", CONF_PASSWORD: "new"}
    assert entry.options == options
    assert hass.config_entries.async_entries(DOMAIN) == [entry]


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
    assert required_field.default() == DEFAULT_DEVICE_UPDATE_INTERVAL_MINUTES

    number_selector = result["data_schema"].schema[required_field]
    assert isinstance(number_selector, selector.NumberSelector)
    assert number_selector.config["unit_of_measurement"] == "min"
    assert number_selector.config["min"] == MIN_DEVICE_UPDATE_INTERVAL_MINUTES
    assert number_selector.config["max"] == MAX_DEVICE_UPDATE_INTERVAL_MINUTES
    assert number_selector.config["step"] == 1

    result = await flow.async_step_init({DEVICE_UPDATE_INTERVAL_KEY: 30})
    assert result["type"].value == "create_entry"
    assert result["data"][DEVICE_UPDATE_INTERVAL_KEY] == 30


@pytest.mark.asyncio
async def test_options_flow_validates_interval(hass: HomeAssistant) -> None:
    """Invalid intervals return the form with an error."""

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = KippyConfigFlow.async_get_options_flow(entry)
    flow.hass = hass

    result = await flow.async_step_init({DEVICE_UPDATE_INTERVAL_KEY: 0})
    assert result["type"].value == "form"
    assert result["errors"]["base"] == "invalid_device_update_interval"

    result = await flow.async_step_init({DEVICE_UPDATE_INTERVAL_KEY: "abc"})
    assert result["type"].value == "form"
    assert result["errors"]["base"] == "invalid_device_update_interval"
