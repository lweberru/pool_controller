from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN = "pool_controller"
MANUFACTURER = "lweberru"

# Konfigurations-Schlüssel
CONF_POOL_NAME = "name"
CONF_WATER_VOLUME = "water_volume"
CONF_MAIN_SWITCH = "main_switch"
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

# Bathing timer
CONF_BATH_DURATION = "bathing_minutes"
DEFAULT_BATH_MINUTES = 60
# Filter cycle defaults
CONF_FILTER_DURATION = "filter_minutes"
CONF_FILTER_INTERVAL = "filter_interval_minutes"
DEFAULT_FILTER_DURATION = 30
DEFAULT_FILTER_INTERVAL = 24 * 60

# PV thresholds (in Watts or sensor units)
CONF_PV_ON_THRESHOLD = "pv_on_threshold"
CONF_PV_OFF_THRESHOLD = "pv_off_threshold"
DEFAULT_PV_ON = 1000
DEFAULT_PV_OFF = 500

# Persisted option keys for timers
OPT_KEY_FILTER_UNTIL = "filter_until"
OPT_KEY_FILTER_NEXT = "next_filter_start"

# Alle Standardwerte (Defaults)
DEFAULT_NAME = "Whirlpool Demo"
DEFAULT_VOL = 1000
DEFAULT_MAIN_SW = "switch.whirlpool"
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