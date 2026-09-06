"""Config flow for Grocy Meal Plan Calendar."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow

from .const import CONF_API_KEY, CONF_URL, DOMAIN


class GrocyCalendarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Grocy calendar config entry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_URL].rstrip("/"))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Grocy Meal Plan", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_URL): str, vol.Required(CONF_API_KEY): str}),
        )
