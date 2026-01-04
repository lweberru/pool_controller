import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import *

class PoolControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    def __init__(self):
        self.data = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_heating()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_POOL_NAME, default="Whirlpool"): str,
                vol.Required(CONF_MAIN_SWITCH, default="switch.whirlpool"): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
                vol.Required(CONF_WATER_VOLUME, default=1000): vol.Coerce(int),
                vol.Required(CONF_DEMO_MODE, default=False): bool,
            })
        )

    async def async_step_heating(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_water_quality()
        return self.async_show_form(
            step_id="heating",
            data_schema=vol.Schema({
                vol.Required(CONF_TEMP_WATER, default="sensor.esp32_5_cd41d8_whirlpool_temperature"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Required(CONF_TEMP_OUTDOOR, default="sensor.hue_outdoor_motion_sensor_1_temperatur"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Optional(CONF_AUX_HEATING_SWITCH, default="switch.whirlpool_heizung"): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
                vol.Optional(CONF_MAIN_POWER_SENSOR, default="sensor.whirlpool_leistung"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
                vol.Optional(CONF_AUX_POWER_SENSOR, default="sensor.whirlpool_heizung_leistung"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
            })
        )

    async def async_step_water_quality(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_logic()
        return self.async_show_form(
            step_id="water_quality",
            data_schema=vol.Schema({
                vol.Optional(CONF_PH_SENSOR, default="sensor.esp32_5_cd41d8_whirlpool_ph"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_CHLORINE_SENSOR, default="sensor.esp32_5_cd41d8_whirlpool_chlor"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_SALT_SENSOR, default="sensor.esp32_5_cd41d8_whirlpool_salt"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_TDS_SENSOR, default="sensor.esp32_5_cd41d8_whirlpool_conductivity"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            })
        )

# In custom_components/pool_controller/config_flow.py (Auszug Schritt logic)
    async def async_step_logic(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(title=self.data[CONF_POOL_NAME], data=self.data)
        
        return self.async_show_form(
            step_id="logic",
            data_schema=vol.Schema({
                vol.Optional(CONF_POOL_CALENDAR, default="calendar.whirlpool"): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Optional(CONF_HOLIDAY_CALENDAR, default="calendar.deutschland_bw"): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Optional(CONF_PV_SURPLUS_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
                vol.Required(CONF_QUIET_START, default="22:00"): str,
                vol.Required(CONF_QUIET_END, default="08:00"): str,
                vol.Required(CONF_QUIET_START_WEEKEND, default="22:00"): str,
                vol.Required(CONF_QUIET_END_WEEKEND, default="10:00"): str,
            })
        )