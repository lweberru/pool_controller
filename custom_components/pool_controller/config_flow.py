import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import *

_LOGGER = logging.getLogger(__name__)


# Shared schema builders to avoid duplication between ConfigFlow and OptionsFlow
def _init_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Required(CONF_POOL_NAME, default=c.get(CONF_POOL_NAME, DEFAULT_NAME)): str,
        vol.Required(CONF_WATER_VOLUME, default=c.get(CONF_WATER_VOLUME, DEFAULT_VOL)): vol.Coerce(int),
        vol.Required(CONF_DEMO_MODE, default=c.get(CONF_DEMO_MODE, False)): bool,
    })

def _switches_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Required(CONF_MAIN_SWITCH, default=c.get(CONF_MAIN_SWITCH, DEFAULT_MAIN_SW)): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
        vol.Optional(CONF_PUMP_SWITCH, default=c.get(CONF_PUMP_SWITCH, DEFAULT_PUMP_SW)): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
        vol.Optional(CONF_FILTER_SWITCH, default=c.get(CONF_FILTER_SWITCH, "")): str,
        vol.Optional(CONF_ENABLE_AUX_HEATING, default=c.get(CONF_ENABLE_AUX_HEATING, False)): bool,
        vol.Optional(CONF_AUX_HEATING_SWITCH, default=c.get(CONF_AUX_HEATING_SWITCH, DEFAULT_AUX_SW)): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
        vol.Optional(CONF_MAIN_POWER_SENSOR, default=c.get(CONF_MAIN_POWER_SENSOR, DEFAULT_MAIN_POWER_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
        vol.Optional(CONF_AUX_POWER_SENSOR, default=c.get(CONF_AUX_POWER_SENSOR, DEFAULT_AUX_POWER_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="power")),
    })

def _water_quality_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Required(CONF_TEMP_WATER, default=c.get(CONF_TEMP_WATER, DEFAULT_TEMP_WATER)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
        vol.Optional(CONF_PH_SENSOR, default=c.get(CONF_PH_SENSOR, DEFAULT_PH_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_CHLORINE_SENSOR, default=c.get(CONF_CHLORINE_SENSOR, DEFAULT_CHLOR_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_SALT_SENSOR, default=c.get(CONF_SALT_SENSOR, DEFAULT_SALT_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_TDS_SENSOR, default=c.get(CONF_TDS_SENSOR, DEFAULT_TDS_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
    })

def _sanitizer_schema(default_mode):
    # returns a single-field schema for sanitizer selection; caller should pass localized `options`
    def _inner(options=None):
        return vol.Schema({
            vol.Required(CONF_SANITIZER_MODE, default=default_mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=(options or []),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        })
    return _inner

def _sanitizer_salt_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Required(CONF_TARGET_SALT_G_L, default=c.get(CONF_TARGET_SALT_G_L, DEFAULT_TARGET_SALT_G_L)): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=10,
                step=0.1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="g/L",
            )
        )
    })

def _climate_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Optional(CONF_TARGET_TEMP, default=c.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP)): vol.Coerce(float),
        vol.Optional(CONF_MIN_TEMP, default=c.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=c.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)): vol.Coerce(float),
        vol.Optional(CONF_TARGET_TEMP_STEP, default=c.get(CONF_TARGET_TEMP_STEP, DEFAULT_TARGET_TEMP_STEP)): vol.Coerce(float),
        vol.Optional(CONF_HEATER_BASE_POWER_W, default=c.get(CONF_HEATER_BASE_POWER_W, DEFAULT_HEATER_BASE_POWER_W)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=20000, step=50, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="W")),
        vol.Optional(CONF_HEATER_AUX_POWER_W, default=c.get(CONF_HEATER_AUX_POWER_W, DEFAULT_HEATER_AUX_POWER_W)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=20000, step=50, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="W")),
        vol.Optional(CONF_COLD_TOLERANCE, default=c.get(CONF_COLD_TOLERANCE, DEFAULT_COLD_TOLERANCE)): vol.Coerce(float),
        vol.Optional(CONF_HOT_TOLERANCE, default=c.get(CONF_HOT_TOLERANCE, DEFAULT_HOT_TOLERANCE)): vol.Coerce(float),
    })

def _costs_schema(curr: dict | None = None):
    c = curr or {}
    schema = {}
    price_default = c.get(CONF_ELECTRICITY_PRICE) if c.get(CONF_ELECTRICITY_PRICE) is not None else None
    price_entity_default = c.get(CONF_ELECTRICITY_PRICE_ENTITY) if c.get(CONF_ELECTRICITY_PRICE_ENTITY) else None
    tariff_default = c.get(CONF_FEED_IN_TARIFF) if c.get(CONF_FEED_IN_TARIFF) is not None else None
    tariff_entity_default = c.get(CONF_FEED_IN_TARIFF_ENTITY) if c.get(CONF_FEED_IN_TARIFF_ENTITY) else None

    schema[
        vol.Optional(CONF_ELECTRICITY_PRICE, default=price_default)
        if price_default is not None
        else vol.Optional(CONF_ELECTRICITY_PRICE)
    ] = selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=5, step=0.001, mode=selector.NumberSelectorMode.BOX))

    schema[
        vol.Optional(CONF_ELECTRICITY_PRICE_ENTITY, default=price_entity_default)
        if price_entity_default is not None
        else vol.Optional(CONF_ELECTRICITY_PRICE_ENTITY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor", "input_number"]))

    schema[
        vol.Optional(CONF_FEED_IN_TARIFF, default=tariff_default)
        if tariff_default is not None
        else vol.Optional(CONF_FEED_IN_TARIFF)
    ] = selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=5, step=0.001, mode=selector.NumberSelectorMode.BOX))

    schema[
        vol.Optional(CONF_FEED_IN_TARIFF_ENTITY, default=tariff_entity_default)
        if tariff_entity_default is not None
        else vol.Optional(CONF_FEED_IN_TARIFF_ENTITY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor", "input_number"]))

    # Optional energy (kWh) sensors for period-based costs
    grid_load_default = c.get(CONF_GRID_TO_LOAD_ENERGY_ENTITY) if c.get(CONF_GRID_TO_LOAD_ENERGY_ENTITY) else None
    grid_load_daily_default = c.get(CONF_GRID_TO_LOAD_ENERGY_ENTITY_DAILY) if c.get(CONF_GRID_TO_LOAD_ENERGY_ENTITY_DAILY) else None
    grid_load_monthly_default = c.get(CONF_GRID_TO_LOAD_ENERGY_ENTITY_MONTHLY) if c.get(CONF_GRID_TO_LOAD_ENERGY_ENTITY_MONTHLY) else None
    grid_load_yearly_default = c.get(CONF_GRID_TO_LOAD_ENERGY_ENTITY_YEARLY) if c.get(CONF_GRID_TO_LOAD_ENERGY_ENTITY_YEARLY) else None
    solar_grid_default = c.get(CONF_SOLAR_TO_GRID_ENERGY_ENTITY) if c.get(CONF_SOLAR_TO_GRID_ENERGY_ENTITY) else None
    solar_load_default = c.get(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY) if c.get(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY) else None
    solar_load_daily_default = c.get(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_DAILY) if c.get(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_DAILY) else None
    solar_load_monthly_default = c.get(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_MONTHLY) if c.get(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_MONTHLY) else None
    solar_load_yearly_default = c.get(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_YEARLY) if c.get(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_YEARLY) else None
    total_load_default = c.get(CONF_TOTAL_LOAD_ENERGY_ENTITY) if c.get(CONF_TOTAL_LOAD_ENERGY_ENTITY) else None

    schema[
        vol.Optional(CONF_GRID_TO_LOAD_ENERGY_ENTITY, default=grid_load_default)
        if grid_load_default is not None
        else vol.Optional(CONF_GRID_TO_LOAD_ENERGY_ENTITY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_GRID_TO_LOAD_ENERGY_ENTITY_DAILY, default=grid_load_daily_default)
        if grid_load_daily_default is not None
        else vol.Optional(CONF_GRID_TO_LOAD_ENERGY_ENTITY_DAILY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_GRID_TO_LOAD_ENERGY_ENTITY_MONTHLY, default=grid_load_monthly_default)
        if grid_load_monthly_default is not None
        else vol.Optional(CONF_GRID_TO_LOAD_ENERGY_ENTITY_MONTHLY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_GRID_TO_LOAD_ENERGY_ENTITY_YEARLY, default=grid_load_yearly_default)
        if grid_load_yearly_default is not None
        else vol.Optional(CONF_GRID_TO_LOAD_ENERGY_ENTITY_YEARLY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_SOLAR_TO_GRID_ENERGY_ENTITY, default=solar_grid_default)
        if solar_grid_default is not None
        else vol.Optional(CONF_SOLAR_TO_GRID_ENERGY_ENTITY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY, default=solar_load_default)
        if solar_load_default is not None
        else vol.Optional(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_DAILY, default=solar_load_daily_default)
        if solar_load_daily_default is not None
        else vol.Optional(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_DAILY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_MONTHLY, default=solar_load_monthly_default)
        if solar_load_monthly_default is not None
        else vol.Optional(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_MONTHLY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_YEARLY, default=solar_load_yearly_default)
        if solar_load_yearly_default is not None
        else vol.Optional(CONF_SOLAR_TO_LOAD_ENERGY_ENTITY_YEARLY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    schema[
        vol.Optional(CONF_TOTAL_LOAD_ENERGY_ENTITY, default=total_load_default)
        if total_load_default is not None
        else vol.Optional(CONF_TOTAL_LOAD_ENERGY_ENTITY)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))

    return vol.Schema(schema)

def _frost_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Optional(CONF_ENABLE_FROST_PROTECTION, default=c.get(CONF_ENABLE_FROST_PROTECTION, True)): bool,
        vol.Optional(CONF_TEMP_OUTDOOR, default=c.get(CONF_TEMP_OUTDOOR, DEFAULT_TEMP_OUTDOOR)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
        vol.Optional(CONF_FROST_START_TEMP, default=c.get(CONF_FROST_START_TEMP, DEFAULT_FROST_START_TEMP)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=-20, max=10, step=0.5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="°C")),
        vol.Optional(CONF_FROST_SEVERE_TEMP, default=c.get(CONF_FROST_SEVERE_TEMP, DEFAULT_FROST_SEVERE_TEMP)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=-30, max=5, step=0.5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="°C")),
        vol.Optional(CONF_FROST_MILD_INTERVAL, default=c.get(CONF_FROST_MILD_INTERVAL, DEFAULT_FROST_MILD_INTERVAL)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=30, max=12 * 60, step=10, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Optional(CONF_FROST_MILD_RUN, default=c.get(CONF_FROST_MILD_RUN, DEFAULT_FROST_MILD_RUN)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=1, max=60, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Optional(CONF_FROST_SEVERE_INTERVAL, default=c.get(CONF_FROST_SEVERE_INTERVAL, DEFAULT_FROST_SEVERE_INTERVAL)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=30, max=12 * 60, step=10, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Optional(CONF_FROST_SEVERE_RUN, default=c.get(CONF_FROST_SEVERE_RUN, DEFAULT_FROST_SEVERE_RUN)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=1, max=60, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Optional(CONF_FROST_QUIET_OVERRIDE_BELOW_TEMP, default=c.get(CONF_FROST_QUIET_OVERRIDE_BELOW_TEMP, DEFAULT_FROST_QUIET_OVERRIDE_BELOW_TEMP)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=-30, max=5, step=0.5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="°C")),
    })

def _calendars_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Optional(CONF_POOL_CALENDAR, default=c.get(CONF_POOL_CALENDAR, DEFAULT_CAL_POOL)): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
        vol.Optional(CONF_HOLIDAY_CALENDAR, default=c.get(CONF_HOLIDAY_CALENDAR, DEFAULT_CAL_HOLIDAY)): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
        vol.Optional(CONF_ENABLE_EVENT_WEATHER_GUARD, default=c.get(CONF_ENABLE_EVENT_WEATHER_GUARD, False)): bool,
        vol.Optional(CONF_EVENT_WEATHER_ENTITY, default=c.get(CONF_EVENT_WEATHER_ENTITY, "")): selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
        vol.Optional(CONF_EVENT_RAIN_PROBABILITY, default=c.get(CONF_EVENT_RAIN_PROBABILITY, DEFAULT_EVENT_RAIN_PROBABILITY)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=100, step=5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="%")),
        vol.Required(CONF_QUIET_START, default=c.get(CONF_QUIET_START, DEFAULT_Q_START)): str,
        vol.Required(CONF_QUIET_END, default=c.get(CONF_QUIET_END, DEFAULT_Q_END)): str,
        vol.Required(CONF_QUIET_START_WEEKEND, default=c.get(CONF_QUIET_START_WEEKEND, DEFAULT_Q_START_WE)): str,
        vol.Required(CONF_QUIET_END_WEEKEND, default=c.get(CONF_QUIET_END_WEEKEND, DEFAULT_Q_END_WE)): str,
    })

def _filter_schema(curr: dict | None = None, lang: str | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Optional(CONF_ENABLE_AUTO_FILTER, default=c.get(CONF_ENABLE_AUTO_FILTER, True)): bool,
        vol.Required(CONF_FILTER_INTERVAL, default=c.get(CONF_FILTER_INTERVAL, DEFAULT_FILTER_INTERVAL)):
            vol.All(vol.Coerce(int), vol.Range(min=60, max=7 * 24 * 60)),
        vol.Required(CONF_FILTER_DURATION, default=c.get(CONF_FILTER_DURATION, DEFAULT_FILTER_DURATION)):
            vol.All(vol.Coerce(int), vol.Range(min=1, max=c.get(CONF_FILTER_INTERVAL, DEFAULT_FILTER_INTERVAL))),
        vol.Optional(CONF_MERGE_WINDOW_MINUTES, default=c.get(CONF_MERGE_WINDOW_MINUTES, DEFAULT_MERGE_WINDOW_MINUTES)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=12 * 60, step=5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Optional(CONF_MIN_GAP_MINUTES, default=c.get(CONF_MIN_GAP_MINUTES, DEFAULT_MIN_GAP_MINUTES)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=6 * 60, step=5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Optional(CONF_MAX_MERGE_RUN_MINUTES, default=c.get(CONF_MAX_MERGE_RUN_MINUTES, DEFAULT_MAX_MERGE_RUN_MINUTES)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=5, max=6 * 60, step=5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Optional(CONF_MIN_CREDIT_MINUTES, default=c.get(CONF_MIN_CREDIT_MINUTES, DEFAULT_MIN_CREDIT_MINUTES)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=60, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Optional(CONF_CREDIT_SOURCES, default=c.get(CONF_CREDIT_SOURCES, DEFAULT_CREDIT_SOURCES)):
            selector.SelectSelector(selector.SelectSelectorConfig(options=_credit_source_options(lang), multiple=True, mode=selector.SelectSelectorMode.LIST)),
    })

def _durations_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Required(CONF_BATH_DURATION, default=c.get(CONF_BATH_DURATION, DEFAULT_BATH_MINUTES)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=1, max=12 * 60, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
        vol.Required(CONF_CHLORINE_DURATION, default=c.get(CONF_CHLORINE_DURATION, DEFAULT_CHLORINE_DURATION)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=2, max=30, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
    })

def _pv_schema(curr: dict | None = None):
    c = curr or {}
    return vol.Schema({
        vol.Optional(CONF_ENABLE_PV_OPTIMIZATION, default=c.get(CONF_ENABLE_PV_OPTIMIZATION, False)): bool,
        vol.Optional(CONF_PV_SURPLUS_SENSOR, default=c.get(CONF_PV_SURPLUS_SENSOR, DEFAULT_PV_SENS)): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_PV_ON_THRESHOLD, default=c.get(CONF_PV_ON_THRESHOLD, DEFAULT_PV_ON)): vol.Coerce(int),
        vol.Optional(CONF_PV_OFF_THRESHOLD, default=c.get(CONF_PV_OFF_THRESHOLD, DEFAULT_PV_OFF)): vol.Coerce(int),
        # PV smoothing/stability/min-run tuning (user-exposed)
        vol.Optional(CONF_PV_SMOOTH_WINDOW_SECONDS, default=c.get(CONF_PV_SMOOTH_WINDOW_SECONDS, DEFAULT_PV_SMOOTH_WINDOW_SECONDS)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s")),
        vol.Optional(CONF_PV_STABILITY_SECONDS, default=c.get(CONF_PV_STABILITY_SECONDS, DEFAULT_PV_STABILITY_SECONDS)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=86400, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s")),
        vol.Optional(CONF_PV_MIN_RUN_MINUTES, default=c.get(CONF_PV_MIN_RUN_MINUTES, DEFAULT_PV_MIN_RUN_MINUTES)):
            selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=24 * 60, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
    })


def _sanitizer_options(lang: str):
    labels = {
        "de": {"chlorine": "Chlor", "saltwater": "Salzwasser", "mixed": "Mischbetrieb (Salz + Chlor)"},
        "en": {"chlorine": "Chlorine", "saltwater": "Saltwater", "mixed": "Mixed (salt + chlorine)"},
        "es": {"chlorine": "Cloro", "saltwater": "Agua salada", "mixed": "Mixto (sal + cloro)"},
        "fr": {"chlorine": "Chlore", "saltwater": "Eau salée", "mixed": "Mixte (sel + chlore)"},
    }.get((lang or "").split("-")[0], None)
    return [
        {"value": "chlorine", "label": (labels or {}).get("chlorine", "chlorine")},
        {"value": "saltwater", "label": (labels or {}).get("saltwater", "saltwater")},
        {"value": "mixed", "label": (labels or {}).get("mixed", "mixed")},
    ]

def _credit_source_options(lang: str | None = None):
    labels = {
        "de": {
            "bathing": "Baden",
            "filter": "Filtern",
            "frost": "Frostschutz",
            "preheat": "Vorheizen",
            "pv": "PV-Überschuss",
            "thermostat": "Thermostat",
            "chlorine": "Chloren",
        },
        "en": {
            "bathing": "Bathing",
            "filter": "Filter",
            "frost": "Frost protection",
            "preheat": "Preheat",
            "pv": "PV surplus",
            "thermostat": "Thermostat",
            "chlorine": "Chlorine",
        },
        "es": {
            "bathing": "Baño",
            "filter": "Filtrar",
            "frost": "Protección contra heladas",
            "preheat": "Precalentar",
            "pv": "Excedente FV",
            "thermostat": "Termostato",
            "chlorine": "Cloro",
        },
        "fr": {
            "bathing": "Bain",
            "filter": "Filtrer",
            "frost": "Protection antigel",
            "preheat": "Préchauffage",
            "pv": "Surplus PV",
            "thermostat": "Thermostat",
            "chlorine": "Chlore",
        },
    }.get((lang or "").split("-")[0], None)

    def _label(key, fallback):
        return (labels or {}).get(key, fallback)

    return [
        {"value": "bathing", "label": _label("bathing", "bathing")},
        {"value": "filter", "label": _label("filter", "filter")},
        {"value": "frost", "label": _label("frost", "frost")},
        {"value": "preheat", "label": _label("preheat", "preheat")},
        {"value": "pv", "label": _label("pv", "pv")},
        {"value": "thermostat", "label": _label("thermostat", "thermostat")},
        {"value": "chlorine", "label": _label("chlorine", "chlorine")},
    ]

class PoolControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    def __init__(self): self.data = {}

    def _sanitizer_select_options(self):
        """Localized labels for sanitizer mode options (best effort)."""
        lang = (getattr(self.hass.config, "language", "en") or "en").split("-")[0]
        return _sanitizer_options(lang)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_switches()
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=_init_schema({}),
            last_step=False
        )
    async def async_step_switches(self, user_input=None):
        """Second step: switches and power sensors."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_water_quality()

        return self.async_show_form(
            step_id="switches",
            data_schema=_switches_schema({}),
            last_step=False
        )

    async def async_step_water_quality(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_sanitizer()

        return self.async_show_form(
            step_id="water_quality",
            data_schema=_water_quality_schema({}),
            last_step=False
        )

    async def async_step_sanitizer(self, user_input=None):
        """Sanitizer selection (chlorine/saltwater/mixed)."""
        if user_input is not None:
            mode = (user_input.get(CONF_SANITIZER_MODE) or DEFAULT_SANITIZER_MODE).strip().lower()
            if mode not in ("chlorine", "saltwater", "mixed"):
                mode = DEFAULT_SANITIZER_MODE
            self.data[CONF_SANITIZER_MODE] = mode
            # Keep legacy flag in sync for backward compatibility.
            self.data[CONF_ENABLE_SALTWATER] = (mode in ("saltwater", "mixed"))
            if mode in ("saltwater", "mixed"):
                return await self.async_step_sanitizer_salt()
            return await self.async_step_climate()

        curr = {**self.data}
        default_mode = (curr.get(CONF_SANITIZER_MODE) or ("saltwater" if curr.get(CONF_ENABLE_SALTWATER) else DEFAULT_SANITIZER_MODE))
        # Provide localized option labels to the selector
        return self.async_show_form(
            step_id="sanitizer",
            data_schema=_sanitizer_schema(default_mode)(self._sanitizer_select_options()),
            last_step=False,
        )

    async def async_step_sanitizer_salt(self, user_input=None):
        """Ask for target salt level when saltwater is enabled."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_climate()

        curr = {**self.data}
        return self.async_show_form(
            step_id="sanitizer_salt",
            data_schema=_sanitizer_salt_schema(curr),
            last_step=False,
        )

    async def async_step_climate(self, user_input=None):
        """Thermostat-like settings for temperature control."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_frost()

        curr = {**self.data}
        errors = {}
        return self.async_show_form(
            step_id="climate",
            errors=errors,
            data_schema=_climate_schema(curr),
            last_step=False,
        )

    async def async_step_frost(self, user_input=None):
        """Frost protection tuning."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_calendars()

        return self.async_show_form(
            step_id="frost",
            data_schema=_frost_schema({}),
            last_step=False,
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
            data_schema=_calendars_schema({}),
            last_step=False
        )

    async def async_step_filter(self, user_input=None):
        """Fifth step: filter interval settings."""
        errors = {}
        if user_input is not None:
            # Filterdauer darf nicht länger als das Intervall sein
            interval = int(user_input.get(CONF_FILTER_INTERVAL, DEFAULT_FILTER_INTERVAL))
            filter_duration = int(user_input.get(CONF_FILTER_DURATION, DEFAULT_FILTER_DURATION))
            if filter_duration > interval:
                filter_duration = interval
                user_input[CONF_FILTER_DURATION] = filter_duration
            self.data.update(user_input)
            return await self.async_step_durations()

        return self.async_show_form(
            step_id="filter",
            errors=errors,
            data_schema=_filter_schema({}, (getattr(self.hass.config, "language", "en") or "en")),
            last_step=False
        )

    async def async_step_durations(self, user_input=None):
        """Step: Dauer-Einstellungen (Baden & Stoßchlorung)."""
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_pv()

        curr = {**self.data}
        return self.async_show_form(
            step_id="durations",
            data_schema=_durations_schema(curr),
            last_step=False,
        )

    async def async_step_pv(self, user_input=None):
        """Sixth step: PV sensor and thresholds."""
        errors = {}
        if user_input is not None:
            try:
                self.data.update(user_input)
                return await self.async_step_costs()
            except Exception:
                _LOGGER.exception("Unerwarteter Fehler im Config Flow")
                errors["base"] = "unknown"

        curr = {**self.data}
        return self.async_show_form(
            step_id="pv",
            errors=errors,
            data_schema=_pv_schema(curr),
            last_step=True
        )

    async def async_step_costs(self, user_input=None):
        """Electricity costs and feed-in tariff."""
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
            step_id="costs",
            errors=errors,
            data_schema=_costs_schema(curr),
            last_step=True,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry): return PoolControllerOptionsFlowHandler(config_entry)

class PoolControllerOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry
        self.options = {}
        self._menu_mode = True

    async def async_step_init(self, user_input=None):
        """Entry point: show a chapter menu for quick edits."""
        self._menu_mode = True
        return self._show_options_menu()

    async def async_step_menu(self, user_input=None):
        """Menu step: render the options menu."""
        self._menu_mode = True
        return self._show_options_menu()

    def _show_options_menu(self):
        return self.async_show_menu(
            step_id="menu",
            menu_options=[
                "basic",
                "switches",
                "water_quality",
                "sanitizer",
                "climate",
                "frost",
                "calendars",
                "filter",
                "durations",
                "pv",
                "costs",
                "all",
            ],
        )

    async def async_step_all(self, user_input=None):
        """Guided full flow (same as before)."""
        self._menu_mode = False
        return await self.async_step_basic(user_input)

    async def async_step_basic(self, user_input=None):
        """Basic pool settings."""
        if user_input is not None:
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_switches()

        curr = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="basic",
            data_schema=_init_schema(curr),
            last_step=False
        )

    async def async_step_switches(self, user_input=None):
        """Second step: switches and power sensors."""
        if user_input is not None:
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_water_quality()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="switches",
            data_schema=_switches_schema(curr),
            last_step=False
        )

    async def async_step_water_quality(self, user_input=None):
        """Third step: water quality sensors."""
        if user_input is not None:
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_sanitizer()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="water_quality",
            data_schema=_water_quality_schema(curr),
            last_step=False
        )

    async def async_step_sanitizer(self, user_input=None):
        """Sanitizer selection (chlorine/saltwater/mixed)."""
        if user_input is not None:
            mode = (user_input.get(CONF_SANITIZER_MODE) or DEFAULT_SANITIZER_MODE).strip().lower()
            if mode not in ("chlorine", "saltwater", "mixed"):
                mode = DEFAULT_SANITIZER_MODE
            self.options[CONF_SANITIZER_MODE] = mode
            # Keep legacy flag in sync for backward compatibility.
            self.options[CONF_ENABLE_SALTWATER] = (mode in ("saltwater", "mixed"))
            if mode in ("saltwater", "mixed"):
                return await self.async_step_sanitizer_salt()
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_climate()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        default_mode = (
            curr.get(CONF_SANITIZER_MODE)
            or ("saltwater" if curr.get(CONF_ENABLE_SALTWATER) else DEFAULT_SANITIZER_MODE)
        )

        # Reuse centralized localized options helper
        lang = (getattr(self.hass.config, "language", "en") or "en").split("-")[0]
        options = _sanitizer_options(lang)

        return self.async_show_form(
            step_id="sanitizer",
            data_schema=_sanitizer_schema(default_mode)(options),
            last_step=False,
        )

    async def async_step_sanitizer_salt(self, user_input=None):
        """Ask for target salt level when saltwater is enabled."""
        if user_input is not None:
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_climate()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="sanitizer_salt",
            data_schema=_sanitizer_salt_schema(curr),
            last_step=False,
        )

    async def async_step_climate(self, user_input=None):
        """Thermostat-like settings for temperature control."""
        if user_input is not None:
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_frost()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="climate",
            data_schema=_climate_schema(curr),
            last_step=False,
        )

    async def async_step_frost(self, user_input=None):
        """Fourth step: frost protection tuning."""
        if user_input is not None:
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_calendars()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="frost",
            data_schema=_frost_schema(curr),
            last_step=False,
        )

    async def async_step_calendars(self, user_input=None):
        """Fourth step: calendars and quiet times."""
        if user_input is not None:
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_filter()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="calendars",
            data_schema=_calendars_schema(curr),
            last_step=False
        )

    async def async_step_filter(self, user_input=None):
        """Fifth step: filter interval settings."""
        if user_input is not None:
            # Defensive: best-effort validate numeric inputs and return form errors
            errors = {}
            try:
                interval = int(user_input.get(CONF_FILTER_INTERVAL, DEFAULT_FILTER_INTERVAL))
            except Exception:
                interval = DEFAULT_FILTER_INTERVAL
                errors[CONF_FILTER_INTERVAL] = "invalid_value"
            try:
                filter_duration = int(user_input.get(CONF_FILTER_DURATION, DEFAULT_FILTER_DURATION))
            except Exception:
                filter_duration = DEFAULT_FILTER_DURATION
                errors[CONF_FILTER_DURATION] = "invalid_value"

            if filter_duration > interval:
                filter_duration = interval
                user_input[CONF_FILTER_DURATION] = filter_duration

            # If there were validation errors, re-show the form with error hints
            if errors:
                # Re-render with the same curr context so defaults are preserved
                curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
                return self.async_show_form(
                    step_id="filter",
                    errors=errors,
                    data_schema=_filter_schema(curr, (getattr(self.hass.config, "language", "en") or "en")),
                    last_step=False
                )

            # Persist normalized values and continue
            user_input[CONF_FILTER_INTERVAL] = interval
            user_input[CONF_FILTER_DURATION] = filter_duration
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_durations()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="filter",
            data_schema=_filter_schema(curr, (getattr(self.hass.config, "language", "en") or "en")),
            last_step=False
        )

    async def async_step_durations(self, user_input=None):
        """Step: Dauer-Einstellungen (Baden & Stoßchlorung)."""
        if user_input is not None:
            self.options.update(user_input)
            if self._menu_mode:
                return self.async_create_entry(title="", data=self.options)
            return await self.async_step_pv()

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="durations",
            data_schema=_durations_schema(curr),
            last_step=False,
        )

    async def async_step_pv(self, user_input=None):
        """Sixth step: PV sensor and thresholds."""
        errors = {}
        if user_input is not None:
            try:
                self.options.update(user_input)
                return await self.async_step_costs()
            except Exception:
                _LOGGER.exception("Fehler im Options Flow (Zahnrad)")
                errors["base"] = "unknown"

        curr = {**self._config_entry.data, **self._config_entry.options, **self.options}
        return self.async_show_form(
            step_id="pv",
            errors=errors,
            data_schema=_pv_schema(curr),
            last_step=True
        )

    async def async_step_costs(self, user_input=None):
        """Electricity costs and feed-in tariff."""
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
            step_id="costs",
            errors=errors,
            data_schema=_costs_schema(curr),
            last_step=True
        )