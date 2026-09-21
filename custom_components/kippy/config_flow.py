"""Config flow for the Kippy integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client, selector
from kippy_api import KippyApi, KippyAuthError, KippyError

from .const import (
    DOMAIN,
    MAX_DEVICE_UPDATE_INTERVAL_MINUTES,
    MIN_DEVICE_UPDATE_INTERVAL_MINUTES,
)
from .helpers import (
    DEVICE_UPDATE_INTERVAL_KEY,
    get_device_update_interval,
    normalize_device_update_interval,
)

_LOGGER = logging.getLogger(__name__)


class KippyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kippy."""

    VERSION = 1

    def is_matching(self, other_flow: config_entries.ConfigFlow) -> bool:
        """Return True when ``other_flow`` targets the same integration."""
        return isinstance(other_flow, KippyConfigFlow)

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()
            if error := await self._async_validate_credentials(
                user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            ):
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _async_validate_credentials(
        self, email: str, password: str
    ) -> str | None:
        """Validate credentials without storing authentication tokens in HA."""
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            api = await KippyApi.async_create(session)
            await api.login(email, password)
        except KippyAuthError:
            return "invalid_auth"
        except KippyError:
            return "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error during login")
            return "unknown"
        return None

    async def async_step_reauth(self, entry_data: dict) -> ConfigFlowResult:
        """Start reauthentication for the existing account."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
        """Replace the password while preserving the account and its entities."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            if error := await self._async_validate_credentials(
                entry.data[CONF_EMAIL], user_input[CONF_PASSWORD]
            ):
                errors["base"] = error
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
                # The options listener adjusts polling; credential changes need a reload.
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return KippyOptionsFlowHandler(config_entry)


class KippyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the options flow for Kippy."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Handle the options step for configuring refresh interval."""

        errors: dict[str, str] = {}

        if user_input is not None:
            minutes = normalize_device_update_interval(
                user_input.get(DEVICE_UPDATE_INTERVAL_KEY)
            )
            if minutes is None:
                errors["base"] = "invalid_device_update_interval"
            else:
                options = dict(self._config_entry.options)
                options[DEVICE_UPDATE_INTERVAL_KEY] = minutes
                return self.async_create_entry(title="", data=options)

        current = get_device_update_interval(self._config_entry)
        data_schema = vol.Schema(
            {
                vol.Required(
                    DEVICE_UPDATE_INTERVAL_KEY,
                    default=current,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_DEVICE_UPDATE_INTERVAL_MINUTES,
                        max=MAX_DEVICE_UPDATE_INTERVAL_MINUTES,
                        step=1,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
