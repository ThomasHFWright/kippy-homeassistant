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

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
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
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=user_input[CONF_EMAIL], data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


