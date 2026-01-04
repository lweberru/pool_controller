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
                vol.Required(CONF_POOL_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_MAIN_SWITCH, default=DEFAULT_MAIN_SW): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
                vol.Required(CONF_WATER_VOLUME, default=DEFAULT_VOL): vol.Coerce(int),
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
                vol.Required(CONF_TEMP_WATER, default=DEFAULT_TEMP_WATER): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Required(CONF_TEMP_OUTDOOR, default=DEFAULT_TEMP_OUTDOOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Optional(CONF_AUX_HEATING_SWITCH, default=DEFAULT_AUX_SW): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
            })
        )

    async def async_step_logic(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(title=self.data[CONF_POOL_NAME], data=self.data)
        
        return self.async_show_form(
            step_id="logic",
            data_schema=vol.Schema({
                vol.Optional(CONF_POOL_CALENDAR, default=DEFAULT_CAL_POOL): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Optional(CONF_HOLIDAY_CALENDAR, default=DEFAULT_CAL_HOLIDAY): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Required(CONF_QUIET_START, default=DEFAULT_Q_START): str,
                vol.Required(CONF_QUIET_END, default=DEFAULT_Q_END): str,
                vol.Required(CONF_QUIET_START_WEEKEND, default=DEFAULT_Q_START_WE): str,
                vol.Required(CONF_QUIET_END_WEEKEND, default=DEFAULT_Q_END_WE): str,
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

        # Aktuelle Werte sicher abrufen (Zahnrad-Fix)
        curr = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_WATER_VOLUME, default=curr.get(CONF_WATER_VOLUME, DEFAULT_VOL)): vol.Coerce(int),
                vol.Required(CONF_QUIET_START, default=curr.get(CONF_QUIET_START, DEFAULT_Q_START)): str,
                vol.Required(CONF_QUIET_END, default=curr.get(CONF_QUIET_END, DEFAULT_Q_END)): str,
                vol.Required(CONF_QUIET_START_WEEKEND, default=curr.get(CONF_QUIET_START_WEEKEND, DEFAULT_Q_START_WE)): str,
                vol.Required(CONF_QUIET_END_WEEKEND, default=curr.get(CONF_QUIET_END_WEEKEND, DEFAULT_Q_END_WE)): str,
            })
        )