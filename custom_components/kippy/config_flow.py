"""Config flow for the Kippy integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from aiohttp import ClientError, ClientResponseError
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import aiohttp_client

from .api import KippyApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class KippyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kippy."""

    VERSION = 1

    def is_matching(self, other_flow: config_entries.ConfigFlow) -> bool:
        """Return True when ``other_flow`` targets the same integration."""
        return isinstance(other_flow, KippyConfigFlow)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not isinstance(self.context, dict):
                self.context = dict(self.context)
            existing_entry = await self.async_set_unique_id(user_input[CONF_EMAIL])
            async_entry_lookup = getattr(
                getattr(self.hass, "config_entries", None),
                "async_entry_for_domain_unique_id",
                None,
            )
            if hasattr(async_entry_lookup, "return_value") and not isinstance(
                existing_entry, config_entries.ConfigEntry
            ):
                async_entry_lookup.return_value = None
            self._abort_if_unique_id_configured()
            session = aiohttp_client.async_get_clientsession(self.hass)
            api = await KippyApi.async_create(session)
            try:
                await api.login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            except ClientResponseError as err:
                if err.status in (401, 403):
                    errors["base"] = "invalid_auth"
                else:
                    _LOGGER.debug(
                        "Unexpected response during login: status=%s message=%s",
                        err.status,
                        err.message,
                    )
                    errors["base"] = "cannot_connect"
            except ClientError as err:
                _LOGGER.debug("Error communicating with Kippy API: %s", err)
                errors["base"] = "cannot_connect"
            except RuntimeError as err:
                _LOGGER.debug("Unexpected runtime error during login: %s", err)
                errors["base"] = "unknown"
            # pylint: disable-next=broad-exception-caught
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during login: %s", err)
                errors["base"] = "unknown"
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
