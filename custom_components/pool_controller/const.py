from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN = "pool_controller"
MANUFACTURER = "lweberru"

# Konfigurations-Schlüssel
CONF_POOL_NAME = "name"
CONF_WATER_VOLUME = "water_volume"
CONF_MAIN_SWITCH = "main_switch"
# Optional: separate circulation/pump switch (if main_switch is only the power supply).
# If not configured, the integration will fall back to CONF_MAIN_SWITCH.
CONF_PUMP_SWITCH = "pump_switch"
CONF_FILTER_SWITCH = "filter_switch"  # Optional: separater Filter-Schalter
CONF_TEMP_WATER = "temp_water_sensor"
CONF_TEMP_OUTDOOR = "temp_outdoor_sensor"
CONF_AUX_HEATING_SWITCH = "aux_heating_switch"
CONF_MAIN_POWER_SENSOR = "main_power_sensor"
CONF_AUX_POWER_SENSOR = "aux_power_sensor"
CONF_PH_SENSOR = "ph_sensor"
CONF_CHLORINE_SENSOR = "chlorine_sensor"
CONF_SALT_SENSOR = "salt_sensor"
CONF_TDS_SENSOR = "tds_sensor"
CONF_PV_SURPLUS_SENSOR = "pv_surplus_sensor"
CONF_POOL_CALENDAR = "pool_calendar"
CONF_HOLIDAY_CALENDAR = "holiday_calendar"
CONF_QUIET_START = "quiet_time_start"
CONF_QUIET_END = "quiet_time_end"
CONF_QUIET_START_WEEKEND = "quiet_time_start_weekend"
CONF_QUIET_END_WEEKEND = "quiet_time_end_weekend"
CONF_DEMO_MODE = "demo_mode"

# Climate / thermostat-like behavior
CONF_TARGET_TEMP = "target_temp"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_TARGET_TEMP_STEP = "target_temp_step"
CONF_COLD_TOLERANCE = "cold_tolerance"
CONF_HOT_TOLERANCE = "hot_tolerance"

# Heating power used for preheat time estimation (watts).
# Do NOT derive this from a live pump power sensor.
CONF_HEATER_POWER_W = "heater_power_w"

# Optional split heating powers (watts) to better model installations where
# the circulation pump contributes some waste heat and the auxiliary heater adds more.
# Effective heating power for preheat = base + (aux if aux heating is enabled).
CONF_HEATER_BASE_POWER_W = "heater_base_power_w"
CONF_HEATER_AUX_POWER_W = "heater_aux_power_w"

# Feature-Toggles (aktivieren/deaktivieren von Funktionen)
CONF_ENABLE_AUTO_FILTER = "enable_auto_filter"
CONF_ENABLE_PV_OPTIMIZATION = "enable_pv_optimization"
CONF_ENABLE_SALTWATER = "enable_saltwater"
CONF_ENABLE_AUX_HEATING = "enable_aux_heating"
CONF_ENABLE_FROST_PROTECTION = "enable_frost_protection"

# Frost protection (duty-cycle) tuning
# Below CONF_FROST_START_TEMP the pump may run periodically to prevent freezing.
# Below CONF_FROST_SEVERE_TEMP the pump runs more often.
# During quiet hours, frost protection will only run if outdoor temperature is <= CONF_FROST_QUIET_OVERRIDE_BELOW_TEMP.
CONF_FROST_START_TEMP = "frost_start_temp"
CONF_FROST_SEVERE_TEMP = "frost_severe_temp"
CONF_FROST_MILD_INTERVAL = "frost_mild_interval_minutes"
CONF_FROST_MILD_RUN = "frost_mild_run_minutes"
CONF_FROST_SEVERE_INTERVAL = "frost_severe_interval_minutes"
CONF_FROST_SEVERE_RUN = "frost_severe_run_minutes"
CONF_FROST_QUIET_OVERRIDE_BELOW_TEMP = "frost_quiet_override_below_temp"

# Bathing timer
CONF_BATH_DURATION = "bathing_minutes"
DEFAULT_BATH_MINUTES = 60
# Filter cycle defaults
CONF_FILTER_DURATION = "filter_minutes"
CONF_FILTER_INTERVAL = "filter_interval_minutes"
DEFAULT_FILTER_DURATION = 30
DEFAULT_FILTER_INTERVAL = 12 * 60  # 12 hours = 720 minutes

# PV thresholds (in Watts or sensor units)
CONF_PV_ON_THRESHOLD = "pv_on_threshold"
CONF_PV_OFF_THRESHOLD = "pv_off_threshold"
DEFAULT_PV_ON = 1000
DEFAULT_PV_OFF = 500

# Persisted option keys for timers
# Manual timer (shared for bathing/chlorine/filter)
OPT_KEY_MANUAL_UNTIL = "manual_timer_until"
OPT_KEY_MANUAL_TYPE = "manual_timer_type"  # bathing | chlorine | filter
OPT_KEY_MANUAL_DURATION = "manual_timer_duration"  # minutes

# Persisted target temperature (so HA restarts keep the setpoint)
OPT_KEY_TARGET_TEMP = "target_temp"

# Auto filter cycle timer (interval-based)
OPT_KEY_AUTO_FILTER_UNTIL = "auto_filter_until"
OPT_KEY_AUTO_FILTER_DURATION = "auto_filter_duration"  # minutes

# Pause timer
OPT_KEY_PAUSE_UNTIL = "pause_until"
OPT_KEY_PAUSE_DURATION = "pause_duration"  # minutes

# Next scheduled auto-filter start
OPT_KEY_FILTER_NEXT = "next_filter_start"

# Maintenance mode (hard lockout)
# When active, all automation is suppressed (including frost protection).
OPT_KEY_MAINTENANCE_ACTIVE = "maintenance_active"

# Alle Standardwerte (Defaults)
DEFAULT_NAME = "Whirlpool Demo"
DEFAULT_VOL = 1000
DEFAULT_MAIN_SW = "switch.whirlpool"
# Default: if not explicitly configured, the pump switch equals main switch.
DEFAULT_PUMP_SW = DEFAULT_MAIN_SW
DEFAULT_AUX_SW = "switch.whirlpool_heizung"
DEFAULT_TEMP_WATER = "sensor.esp32_5_cd41d8_whirlpool_temperature"
DEFAULT_TEMP_OUTDOOR = "sensor.hue_outdoor_motion_sensor_1_temperatur"
DEFAULT_MAIN_POWER_SENS = "sensor.whirlpool_leistung"
DEFAULT_AUX_POWER_SENS = "sensor.whirlpool_heizung_leistung"
DEFAULT_PH_SENS = "sensor.esp32_5_cd41d8_whirlpool_ph"
DEFAULT_CHLOR_SENS = "sensor.esp32_5_cd41d8_whirlpool_chlor"
DEFAULT_SALT_SENS = "sensor.esp32_5_cd41d8_whirlpool_salt"
DEFAULT_TDS_SENS = "sensor.esp32_5_cd41d8_whirlpool_conductivity"
DEFAULT_PV_SENS = "sensor.scb_solar_power" 
DEFAULT_CAL_POOL = "calendar.whirlpool"
DEFAULT_CAL_HOLIDAY = "calendar.deutschland_bw"
DEFAULT_Q_START = "22:00"
DEFAULT_Q_END = "08:00"
DEFAULT_Q_START_WE = "22:00"
DEFAULT_Q_END_WE = "10:00"

# Climate defaults
DEFAULT_TARGET_TEMP = 38.0
DEFAULT_MIN_TEMP = 10.0
DEFAULT_MAX_TEMP = 40.0
DEFAULT_TARGET_TEMP_STEP = 0.5

# Default heater power used for preheat estimation
DEFAULT_HEATER_POWER_W = 3000

# Default split powers (disabled by default -> use DEFAULT_HEATER_POWER_W)
DEFAULT_HEATER_BASE_POWER_W = 0
DEFAULT_HEATER_AUX_POWER_W = DEFAULT_HEATER_POWER_W

# Thermostat-like tolerances (hysteresis)
# Defaults preserve current behavior as close as possible, while allowing proper 'stop at target'.
DEFAULT_COLD_TOLERANCE = 1.0
DEFAULT_HOT_TOLERANCE = 0.0

# Frost duty-cycle defaults (intentionally conservative / neighbor-friendly)
DEFAULT_FROST_START_TEMP = 2.0
DEFAULT_FROST_SEVERE_TEMP = -2.0
DEFAULT_FROST_MILD_INTERVAL = 240  # every 4 hours
DEFAULT_FROST_MILD_RUN = 5  # minutes
DEFAULT_FROST_SEVERE_INTERVAL = 120  # every 2 hours
DEFAULT_FROST_SEVERE_RUN = 10  # minutes
DEFAULT_FROST_QUIET_OVERRIDE_BELOW_TEMP = -8.0