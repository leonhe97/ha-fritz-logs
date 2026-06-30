import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    CATEGORY_LABELS,
    CONF_CATEGORIES,
    CONF_POLL_INTERVAL,
    CONF_SSL,
    DEFAULT_CATEGORIES,
    DEFAULT_HOST,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SSL,
    DEFAULT_USERNAME,
    DOMAIN,
)
from .fritz_session import FritzAuthError, FritzSession

_LOGGER = logging.getLogger(__name__)


class FritzLogsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FritzLogsOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            try:
                fritz = FritzSession(
                    host=user_input[CONF_HOST],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    ssl=user_input[CONF_SSL],
                )
                await fritz.fetch_logs(async_get_clientsession(self.hass))
            except FritzAuthError:
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.warning("Fritz!Box connection test failed for %s: %s", user_input[CONF_HOST], err)
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"Fritz!Box ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
                vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                    cv.positive_int, vol.Range(min=10, max=3600)
                ),
                vol.Optional(CONF_CATEGORIES, default=DEFAULT_CATEGORIES): cv.multi_select(CATEGORY_LABELS),
            }),
            errors=errors,
        )


class FritzLogsOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_POLL_INTERVAL,
            self._config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        )
        current_categories = self._config_entry.options.get(
            CONF_CATEGORIES,
            self._config_entry.data.get(CONF_CATEGORIES, DEFAULT_CATEGORIES),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_POLL_INTERVAL, default=current_interval): vol.All(
                    cv.positive_int, vol.Range(min=10, max=3600)
                ),
                vol.Optional(CONF_CATEGORIES, default=current_categories): cv.multi_select(CATEGORY_LABELS),
            }),
        )
