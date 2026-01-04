import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import *

class PoolControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.data = user_input
            return await self.async_step_heating()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_POOL_NAME, default="Whirlpool Demo"): str,
                vol.Required(CONF_MAIN_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
                vol.Required(CONF_WATER_VOLUME, default=1000): vol.Coerce(int),
                vol.Required(CONF_DEMO_MODE, default=False): bool,
            })
        )

    async def async_step_heating(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_logic()
        return self.async_show_form(
            step_id="heating",
            data_schema=vol.Schema({
                vol.Required(CONF_TEMP_WATER): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Required(CONF_TEMP_OUTDOOR, default="sensor.hue_outdoor_motion_sensor_1_temperatur"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Optional(CONF_AUX_HEATING_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
            })
        )

    async def async_step_logic(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(title=self.data[CONF_POOL_NAME], data=self.data)
        return self.async_show_form(
            step_id="logic",
            data_schema=vol.Schema({
                vol.Optional(CONF_POOL_CALENDAR): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Optional(CONF_HOLIDAY_CALENDAR): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Required(CONF_QUIET_START, default="22:00"): str,
                vol.Required(CONF_QUIET_END, default="08:00"): str,
                vol.Required(CONF_QUIET_START_WEEKEND, default="22:00"): str,
                vol.Required(CONF_QUIET_END_WEEKEND, default="10:00"): str,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PoolControllerOptionsFlowHandler(config_entry)

class PoolControllerOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_WATER_VOLUME, default=self.config_entry.data.get(CONF_WATER_VOLUME)): vol.Coerce(int),
                vol.Required(CONF_QUIET_START, default=self.config_entry.data.get(CONF_QUIET_START)): str,
                vol.Required(CONF_QUIET_END, default=self.config_entry.data.get(CONF_QUIET_END)): str,
                vol.Required(CONF_QUIET_START_WEEKEND, default=self.config_entry.data.get(CONF_QUIET_START_WEEKEND)): str,
                vol.Required(CONF_QUIET_END_WEEKEND, default=self.config_entry.data.get(CONF_QUIET_END_WEEKEND)): str,
            })
        )