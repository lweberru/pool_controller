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
            return await self.async_step_switches()
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema({
                vol.Required(CONF_POOL_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_WATER_VOLUME, default=DEFAULT_VOL): vol.Coerce(int),
                vol.Required(CONF_DEMO_MODE, default=False): bool,
            }),
            last_step=False
        )
    async def async_step_switches(self, user_input=None):
        """Second step: switches and power sensors."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_water_quality()

        return self.async_show_form(
            step_id="switches",
            data_schema=vol.Schema({
                vol.Required(CONF_MAIN_SWITCH, default=DEFAULT_MAIN_SW): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
                vol.Optional(CONF_FILTER_SWITCH): str,
                vol.Optional(CONF_ENABLE_AUX_HEATING, default=False): bool,
                vol.Optional(CONF_AUX_HEATING_SWITCH, default=DEFAULT_AUX_SW): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
                vol.Optional(CONF_MAIN_POWER_SENSOR, default=DEFAULT_MAIN_POWER_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
                vol.Optional(CONF_AUX_POWER_SENSOR, default=DEFAULT_AUX_POWER_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
            }),
            last_step=False
        )

    async def async_step_water_quality(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_calendars()

        return self.async_show_form(
            step_id="water_quality",
            data_schema=vol.Schema({
                vol.Required(CONF_TEMP_WATER, default=DEFAULT_TEMP_WATER): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Optional(CONF_ENABLE_FROST_PROTECTION, default=True): bool,
                vol.Optional(CONF_TEMP_OUTDOOR, default=DEFAULT_TEMP_OUTDOOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Optional(CONF_PH_SENSOR, default=DEFAULT_PH_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_CHLORINE_SENSOR, default=DEFAULT_CHLOR_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_ENABLE_SALTWATER, default=False): bool,
                vol.Optional(CONF_SALT_SENSOR, default=DEFAULT_SALT_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_TDS_SENSOR, default=DEFAULT_TDS_SENS): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            }),
            last_step=False
        )

    async def async_step_calendars(self, user_input=None):
        """Fourth step: calendars and quiet times."""
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_filter()

        return self.async_show_form(
            step_id="calendars",
            errors=errors,
            data_schema=vol.Schema({
                vol.Optional(CONF_POOL_CALENDAR, default=DEFAULT_CAL_POOL): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Optional(CONF_HOLIDAY_CALENDAR, default=DEFAULT_CAL_HOLIDAY): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Required(CONF_QUIET_START, default=DEFAULT_Q_START): str,
                vol.Required(CONF_QUIET_END, default=DEFAULT_Q_END): str,
                vol.Required(CONF_QUIET_START_WEEKEND, default=DEFAULT_Q_START_WE): str,
                vol.Required(CONF_QUIET_END_WEEKEND, default=DEFAULT_Q_END_WE): str,
            }),
            last_step=False
        )

    async def async_step_filter(self, user_input=None):
        """Fifth step: filter interval settings."""
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_pv()

        return self.async_show_form(
            step_id="filter",
            errors=errors,
            data_schema=vol.Schema({
                vol.Optional(CONF_ENABLE_AUTO_FILTER, default=True): bool,
                vol.Required(CONF_FILTER_INTERVAL, default=DEFAULT_FILTER_INTERVAL): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=60, max=7*24*60)  # 1 Stunde bis 7 Tage
                ),
            }),
            last_step=False
        )

    async def async_step_pv(self, user_input=None):
        """Sixth step: PV sensor and thresholds."""
        errors = {}
        if user_input is not None:
            try:
                self.data.update(user_input)
                return self.async_create_entry(title=self.data[CONF_POOL_NAME], data=self.data)
            except Exception:
                _LOGGER.exception("Unerwarteter Fehler im Config Flow")
                errors["base"] = "unknown"

        curr = {**self.data}
        return self.async_show_form(
            step_id="pv",
            errors=errors,
            data_schema=vol.Schema({
                vol.Optional(CONF_ENABLE_PV_OPTIMIZATION, default=False): bool,
                vol.Optional(CONF_PV_SURPLUS_SENSOR, default=curr.get(CONF_PV_SURPLUS_SENSOR, DEFAULT_PV_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_PV_ON_THRESHOLD, default=curr.get(CONF_PV_ON_THRESHOLD, DEFAULT_PV_ON)): vol.Coerce(int),
                vol.Optional(CONF_PV_OFF_THRESHOLD, default=curr.get(CONF_PV_OFF_THRESHOLD, DEFAULT_PV_OFF)): vol.Coerce(int),
            }),
            last_step=True
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry): return PoolControllerOptionsFlowHandler(config_entry)

class PoolControllerOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry
        self.options = {}

    async def async_step_init(self, user_input=None):
        """First step: pool settings."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_switches()

        curr = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_POOL_NAME, default=curr.get(CONF_POOL_NAME, DEFAULT_NAME)): str,
                vol.Required(CONF_WATER_VOLUME, default=curr.get(CONF_WATER_VOLUME, DEFAULT_VOL)): vol.Coerce(int),
                vol.Required(CONF_DEMO_MODE, default=curr.get(CONF_DEMO_MODE, False)): bool,
            }),
            last_step=False
        )

    async def async_step_switches(self, user_input=None):
        """Second step: switches and power sensors."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_water_quality()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="switches",
            data_schema=vol.Schema({
                vol.Required(CONF_MAIN_SWITCH, default=curr.get(CONF_MAIN_SWITCH, DEFAULT_MAIN_SW)): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
                vol.Optional(CONF_FILTER_SWITCH, default=curr.get(CONF_FILTER_SWITCH, "")): str,
                vol.Optional(CONF_ENABLE_AUX_HEATING, default=curr.get(CONF_ENABLE_AUX_HEATING, False)): bool,
                vol.Optional(CONF_AUX_HEATING_SWITCH, default=curr.get(CONF_AUX_HEATING_SWITCH, DEFAULT_AUX_SW)): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
                vol.Optional(CONF_MAIN_POWER_SENSOR, default=curr.get(CONF_MAIN_POWER_SENSOR, DEFAULT_MAIN_POWER_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
                vol.Optional(CONF_AUX_POWER_SENSOR, default=curr.get(CONF_AUX_POWER_SENSOR, DEFAULT_AUX_POWER_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
            }),
            last_step=False
        )

    async def async_step_water_quality(self, user_input=None):
        """Third step: water quality sensors."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_calendars()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="water_quality",
            data_schema=vol.Schema({
                vol.Required(CONF_TEMP_WATER, default=curr.get(CONF_TEMP_WATER, DEFAULT_TEMP_WATER)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Optional(CONF_ENABLE_FROST_PROTECTION, default=curr.get(CONF_ENABLE_FROST_PROTECTION, True)): bool,
                vol.Optional(CONF_TEMP_OUTDOOR, default=curr.get(CONF_TEMP_OUTDOOR, DEFAULT_TEMP_OUTDOOR)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
                vol.Optional(CONF_PH_SENSOR, default=curr.get(CONF_PH_SENSOR, DEFAULT_PH_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_CHLORINE_SENSOR, default=curr.get(CONF_CHLORINE_SENSOR, DEFAULT_CHLOR_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_ENABLE_SALTWATER, default=curr.get(CONF_ENABLE_SALTWATER, False)): bool,
                vol.Optional(CONF_SALT_SENSOR, default=curr.get(CONF_SALT_SENSOR, DEFAULT_SALT_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_TDS_SENSOR, default=curr.get(CONF_TDS_SENSOR, DEFAULT_TDS_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            }),
            last_step=False
        )

    async def async_step_calendars(self, user_input=None):
        """Fourth step: calendars and quiet times."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_filter()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="calendars",
            data_schema=vol.Schema({
                vol.Optional(CONF_POOL_CALENDAR, default=curr.get(CONF_POOL_CALENDAR, DEFAULT_CAL_POOL)): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Optional(CONF_HOLIDAY_CALENDAR, default=curr.get(CONF_HOLIDAY_CALENDAR, DEFAULT_CAL_HOLIDAY)): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
                vol.Required(CONF_QUIET_START, default=curr.get(CONF_QUIET_START, DEFAULT_Q_START)): str,
                vol.Required(CONF_QUIET_END, default=curr.get(CONF_QUIET_END, DEFAULT_Q_END)): str,
                vol.Required(CONF_QUIET_START_WEEKEND, default=curr.get(CONF_QUIET_START_WEEKEND, DEFAULT_Q_START_WE)): str,
                vol.Required(CONF_QUIET_END_WEEKEND, default=curr.get(CONF_QUIET_END_WEEKEND, DEFAULT_Q_END_WE)): str,
            }),
            last_step=False
        )

    async def async_step_filter(self, user_input=None):
        """Fifth step: filter interval settings."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_pv()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="filter",
            data_schema=vol.Schema({
                vol.Optional(CONF_ENABLE_AUTO_FILTER, default=curr.get(CONF_ENABLE_AUTO_FILTER, True)): bool,
                vol.Required(CONF_FILTER_INTERVAL, default=curr.get(CONF_FILTER_INTERVAL, DEFAULT_FILTER_INTERVAL)): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=60, max=7*24*60)
                ),
            }),
            last_step=False
        )

    async def async_step_pv(self, user_input=None):
        """Sixth step: PV sensor and thresholds."""
        errors = {}
        if user_input is not None:
            try:
                self.options.update(user_input)
                return self.async_create_entry(title="", data=self.options)
            except Exception:
                _LOGGER.exception("Fehler im Options Flow (Zahnrad)")
                errors["base"] = "unknown"

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="pv",
            errors=errors,
            data_schema=vol.Schema({
                vol.Optional(CONF_ENABLE_PV_OPTIMIZATION, default=curr.get(CONF_ENABLE_PV_OPTIMIZATION, False)): bool,
                vol.Optional(CONF_PV_SURPLUS_SENSOR, default=curr.get(CONF_PV_SURPLUS_SENSOR, DEFAULT_PV_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_PV_ON_THRESHOLD, default=curr.get(CONF_PV_ON_THRESHOLD, DEFAULT_PV_ON)): vol.Coerce(int),
                vol.Optional(CONF_PV_OFF_THRESHOLD, default=curr.get(CONF_PV_OFF_THRESHOLD, DEFAULT_PV_OFF)): vol.Coerce(int),
            }),
            last_step=True
        )