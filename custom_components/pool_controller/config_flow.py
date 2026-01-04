import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import *

_LOGGER = logging.getLogger(__name__)

class PoolControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    def __init__(self): self.data = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_heating()
        return self.async_show_form(step_id="user", errors=errors, data_schema=vol.Schema({
            vol.Required(CONF_POOL_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_MAIN_SWITCH, default=DEFAULT_MAIN_SW): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
            vol.Required(CONF_WATER_VOLUME, default=DEFAULT_VOL): vol.Coerce(int),
            vol.Required(CONF_DEMO_MODE, default=False): bool,
        }))

    async def async_step_heating(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_water_quality()
        return self.async_show_form(step_id="heating", data_schema=vol.Schema({
            vol.Required(CONF_TEMP_WATER, default=DEFAULT_TEMP_WATER): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
            vol.Required(CONF_TEMP_OUTDOOR, default=DEFAULT_TEMP_OUTDOOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
            vol.Optional(CONF_AUX_HEATING_SWITCH, default=DEFAULT_AUX_SW): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
            vol.Optional(CONF_MAIN_POWER_SENSOR, default=DEFAULT_MAIN_POWER_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
            vol.Optional(CONF_AUX_POWER_SENSOR, default=DEFAULT_AUX_POWER_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
        }))

    async def async_step_water_quality(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_logic()
        return self.async_show_form(step_id="water_quality", data_schema=vol.Schema({
            vol.Optional(CONF_PH_SENSOR, default=DEFAULT_PH_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_CHLORINE_SENSOR, default=DEFAULT_CHLOR_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_SALT_SENSOR, default=DEFAULT_SALT_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_TDS_SENSOR, default=DEFAULT_TDS_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        }))

    async def async_step_logic(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self.data.update(user_input)
                return self.async_create_entry(title=self.data[CONF_POOL_NAME], data=self.data)
            except Exception:
                _LOGGER.exception("Unerwarteter Fehler im Config Flow")
                errors["base"] = "unknown"

        return self.async_show_form(step_id="logic", errors=errors, data_schema=vol.Schema({
            vol.Optional(CONF_POOL_CALENDAR, default=DEFAULT_CAL_POOL): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
            vol.Optional(CONF_HOLIDAY_CALENDAR, default=DEFAULT_CAL_HOLIDAY): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
            vol.Optional(CONF_PV_SURPLUS_SENSOR, default=DEFAULT_PV_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_QUIET_START, default=DEFAULT_Q_START): str,
            vol.Required(CONF_QUIET_END, default=DEFAULT_Q_END): str,
            vol.Required(CONF_QUIET_START_WEEKEND, default=DEFAULT_Q_START_WE): str,
            vol.Required(CONF_QUIET_END_WEEKEND, default=DEFAULT_Q_END_WE): str,
        }))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry): return PoolControllerOptionsFlowHandler(config_entry)

class PoolControllerOptionsFlowHandler(config_entries.OptionsFlow):
    # def __init__(self, config_entry): self.config_entry = config_entry
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                return self.async_create_entry(title="", data=user_input)
            except Exception:
                _LOGGER.exception("Fehler im Options Flow (Zahnrad)")
                errors["base"] = "unknown"

        curr = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", errors=errors, data_schema=vol.Schema({
            vol.Required(CONF_WATER_VOLUME, default=curr.get(CONF_WATER_VOLUME, DEFAULT_VOL)): vol.Coerce(int),
            vol.Required(CONF_QUIET_START, default=curr.get(CONF_QUIET_START, DEFAULT_Q_START)): str,
            vol.Required(CONF_QUIET_END, default=curr.get(CONF_QUIET_END, DEFAULT_Q_END)): str,
            vol.Required(CONF_QUIET_START_WEEKEND, default=curr.get(CONF_QUIET_START_WEEKEND, DEFAULT_Q_START_WE)): str,
            vol.Required(CONF_QUIET_END_WEEKEND, default=curr.get(CONF_QUIET_END_WEEKEND, DEFAULT_Q_END_WE)): str,
            vol.Optional(CONF_PH_SENSOR, default=curr.get(CONF_PH_SENSOR, DEFAULT_PH_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_CHLORINE_SENSOR, default=curr.get(CONF_CHLORINE_SENSOR, DEFAULT_CHLOR_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        }))