
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class CurrentUVIndexConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Open Meteo Pollen", data=user_input)

        schema = vol.Schema({
            vol.Required("latitude", default=self.hass.config.latitude): float,
            vol.Required("longitude", default=self.hass.config.longitude): float,
            vol.Required("update_interval", default=30): vol.All(int, vol.Range(min=5, max=240)),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CurrentUVIndexOptionsFlow(config_entry)

class CurrentUVIndexOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(
                "update_interval",
                default=self.config_entry.options.get("update_interval", self.config_entry.data.get("update_interval", 30))
            ): vol.All(int, vol.Range(min=5, max=240))
        })
        return self.async_show_form(step_id="init", data_schema=schema)
