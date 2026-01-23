from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    MANUFACTURER,
    CONF_FILTER_DURATION,
    DEFAULT_FILTER_DURATION,
    CONF_CHLORINE_DURATION,
    DEFAULT_CHLORINE_DURATION,
    CONF_BATH_DURATION,
    DEFAULT_BATH_MINUTES,
    CONF_PV_ON_THRESHOLD,
    CONF_PV_OFF_THRESHOLD,
    DEFAULT_PV_ON,
    DEFAULT_PV_OFF,
)


_AUTO_STATE_CLASS = object()
_DEVICE_CLASS_PH = getattr(SensorDeviceClass, "PH", None)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PoolStatusSensor(coordinator),
        PoolRunReasonSensor(coordinator),
        PoolHeatReasonSensor(coordinator),
        PoolSanitizerModeSensor(coordinator),
        # SensorDeviceClass.PH expects no unit_of_measurement.
        PoolChemSensor(coordinator, "ph_val", None, None, "mdi:ph", device_class=_DEVICE_CLASS_PH, state_class=SensorStateClass.MEASUREMENT),
        PoolChemSensor(coordinator, "chlor_val", None, "mV", "mdi:pool"),
        PoolChemSensor(coordinator, "salt_val", None, "g/L", "mdi:shaker"),
        PoolChemSensor(coordinator, "tds_val", None, "ppm", "mdi:water-opacity"),
        PoolChemSensor(coordinator, "tds_effective", None, "ppm", "mdi:water-opacity"),
        # Recommendations (not measurements): keep units but do not set state_class.
        PoolChemSensor(coordinator, "salt_add_g", None, "g", "mdi:shaker", device_class=SensorDeviceClass.WEIGHT, state_class=None, entity_category=EntityCategory.DIAGNOSTIC),
        PoolChemSensor(coordinator, "tds_water_change_liters", None, "L", "mdi:water-sync", device_class=SensorDeviceClass.VOLUME, state_class=None, entity_category=EntityCategory.DIAGNOSTIC),
        PoolChemSensor(coordinator, "tds_water_change_percent", None, "%", "mdi:water-percent", state_class=None, entity_category=EntityCategory.DIAGNOSTIC),
        PoolChemSensor(coordinator, "ph_minus_g", None, "g", "mdi:pill", device_class=SensorDeviceClass.WEIGHT, state_class=None, entity_category=EntityCategory.DIAGNOSTIC),
        PoolChemSensor(coordinator, "ph_plus_g", None, "g", "mdi:pill", device_class=SensorDeviceClass.WEIGHT, state_class=None, entity_category=EntityCategory.DIAGNOSTIC),
        PoolChemSensor(coordinator, "chlor_spoons", None, "Löffel", "mdi:spoon-sugar", state_class=None, entity_category=EntityCategory.DIAGNOSTIC),
        PoolChemSensor(coordinator, "next_start_mins", None, "min", "mdi:clock-start", device_class=SensorDeviceClass.DURATION),
        PoolChemSensor(coordinator, "next_frost_mins", None, "min", "mdi:clock-start", device_class=SensorDeviceClass.DURATION, state_class=None, entity_category=EntityCategory.DIAGNOSTIC),
        PoolChemSensor(coordinator, "event_rain_probability", None, "%", "mdi:weather-rainy", state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC),
        PoolTimeSensor(coordinator, "next_event", None)
    ]
    # Timer/Status sensors
    entities.extend([
        PoolTdsStatusSensor(coordinator),
        PoolTimerSensor(coordinator, "manual_timer_mins", "mdi:timer", kind="manual"),
        PoolTimerSensor(coordinator, "auto_filter_timer_mins", "mdi:timer-cog", kind="auto_filter"),
        PoolTimerSensor(coordinator, "pause_timer_mins", "mdi:pause-circle", kind="pause"),
        PoolTimerSensor(coordinator, "frost_timer_mins", "mdi:snowflake-clock", kind="frost"),
            PoolChemSensor(coordinator, "next_filter_mins", None, "min", "mdi:clock-start", device_class=SensorDeviceClass.DURATION),
        PoolChemSensor(
            coordinator,
            "outdoor_temp",
            None,
            UnitOfTemperature.CELSIUS,
            "mdi:thermometer",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        PoolTimeSensor(coordinator, "next_event_end", None),
        PoolTextSensor(coordinator, "next_event_summary", None),
    ])
    # Power sensors
    entities.extend([
        PoolPowerSensor(coordinator, "pv_power", None),
        PoolPowerSensor(coordinator, "pv_smoothed", None),
        PoolPowerSensor(coordinator, "pv_band_low", None),
        PoolPowerSensor(coordinator, "pv_band_mid_on", None),
        PoolPowerSensor(coordinator, "pv_band_mid_off", None),
        PoolPowerSensor(coordinator, "pv_band_high", None),
        PoolPowerSensor(coordinator, "main_power", None),
        PoolPowerSensor(coordinator, "aux_power", None),
    ])
    async_add_entities(entities)

    # Config value sensors: expose configured durations so the frontend can read them
    try:
        cfg_sensors = [
            PoolConfigSensor(coordinator, CONF_FILTER_DURATION, DEFAULT_FILTER_DURATION, None),
            PoolConfigSensor(coordinator, CONF_CHLORINE_DURATION, DEFAULT_CHLORINE_DURATION, None),
            PoolConfigSensor(coordinator, CONF_BATH_DURATION, DEFAULT_BATH_MINUTES, None),
            PoolConfigSensor(coordinator, CONF_PV_ON_THRESHOLD, DEFAULT_PV_ON, None, unit="W", icon="mdi:flash"),
            PoolConfigSensor(coordinator, CONF_PV_OFF_THRESHOLD, DEFAULT_PV_OFF, None, unit="W", icon="mdi:flash"),
        ]
        async_add_entities(cfg_sensors)
    except Exception:
        # Best-effort: don't crash setup if config sensors fail
        pass

class PoolBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, name=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        # Optional human-friendly fallback name when translations/registry
        # do not provide a translation_key/original_name yet.
        if name:
            self._attr_name = name
    @property
    def device_info(self): return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class PoolStatusSensor(PoolBaseSensor):
    _attr_translation_key = "status"
    @property
    def native_value(self):
        if self.coordinator.data.get("maintenance_active"): return "maintenance"
        if self.coordinator.data.get("frost_danger"): return "frost_protection"
        if self.coordinator.data.get("pause_timer_active"): return "paused"
        return "normal"

class PoolRunReasonSensor(PoolBaseSensor):
    _attr_translation_key = "run_reason"
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_run_reason"

    @property
    def native_value(self):
        return self.coordinator.data.get("run_reason") or "idle"

    @property
    def available(self) -> bool:
        # Prefer cached coordinator data to avoid brief "unavailable" spikes.
        return self.coordinator.data is not None or self.coordinator.last_update_success


class PoolHeatReasonSensor(PoolBaseSensor):
    _attr_translation_key = "heat_reason"
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_heat_reason"

    @property
    def native_value(self):
        return self.coordinator.data.get("heat_reason") or "off"

    @property
    def available(self) -> bool:
        # Prefer cached coordinator data to avoid brief "unavailable" spikes.
        return self.coordinator.data is not None or self.coordinator.last_update_success


class PoolSanitizerModeSensor(PoolBaseSensor):
    _attr_translation_key = "sanitizer_mode"
    _attr_icon = "mdi:water-check"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_sanitizer_mode"

    @property
    def native_value(self):
        mode = (self.coordinator.data.get("sanitizer_mode") or "").strip().lower()
        return mode if mode in ("chlorine", "saltwater", "mixed") else "chlorine"

class PoolTdsStatusSensor(PoolBaseSensor):
    _attr_translation_key = "tds_status"
    _attr_icon = "mdi:water-check"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_tds_status"
    @property
    def native_value(self):
        status = self.coordinator.data.get("tds_status")
        return status if status else "unknown"

class PoolChemSensor(PoolBaseSensor):
    def __init__(
        self,
        coordinator,
        key,
        name,
        unit,
        icon,
        *,
        device_class=None,
        state_class=_AUTO_STATE_CLASS,
        entity_category=None,
    ):
        super().__init__(coordinator, name)
        self._key = key
        self._attr_translation_key = key
        # Names are provided via translation keys in strings.json; do not hardcode here
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        # Auto-default: treat numeric unit-based sensors as measurements unless explicitly disabled.
        if state_class is _AUTO_STATE_CLASS:
            state_class = SensorStateClass.MEASUREMENT if unit is not None else None
        self._attr_state_class = state_class  # may be None (e.g. recommendations)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)

class PoolTimeSensor(PoolBaseSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, name)
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)

class PoolPowerSensor(PoolBaseSensor):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, name)
        self._key = key
        self._attr_translation_key = key
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)
    @property
    def available(self): return self.coordinator.data.get(self._key) is not None

class PoolTextSensor(PoolBaseSensor):
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, name)
        self._key = key
        self._attr_translation_key = key
        self._attr_icon = "mdi:calendar-text"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)


class PoolTimerSensor(PoolBaseSensor):
    _attr_native_unit_of_measurement = "min"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.DURATION

    def __init__(self, coordinator, key, icon, kind: str):
        super().__init__(coordinator)
        self._key = key
        self._kind = kind
        self._attr_translation_key = key
        self._attr_icon = icon
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"

    @property
    def native_value(self):
        val = self.coordinator.data.get(self._key)
        # For frost timer, return None when inactive to avoid showing "0 min"
        if self._kind == "frost":
            if not bool(self.coordinator.data.get("frost_timer_active")):
                return None
        try:
            return int(val) if val is not None else 0
        except Exception:
            return None if self._kind == "frost" else 0

    @property
    def extra_state_attributes(self):
        if self._kind == "manual":
            return {
                "active": bool(self.coordinator.data.get("manual_timer_active")),
                "duration_minutes": self.coordinator.manual_timer_duration,
                "type": self.coordinator.manual_timer_type,
            }
        if self._kind == "auto_filter":
            return {
                "active": bool(self.coordinator.data.get("auto_filter_timer_active")),
                "duration_minutes": self.coordinator.auto_filter_duration,
            }
        if self._kind == "pause":
            return {
                "active": bool(self.coordinator.data.get("pause_timer_active")),
                "duration_minutes": self.coordinator.pause_duration,
            }
        if self._kind == "frost":
            return {
                "active": bool(self.coordinator.data.get("frost_timer_active")),
                "duration_minutes": self.coordinator.frost_timer_duration,
                "type": "frost",
            }
        return {}


class PoolConfigSensor(PoolBaseSensor):
    """Expose a configured option value as a simple sensor.

    This reads from the config entry data/options with a sensible default.
    """
    _attr_state_class = None

    def __init__(self, coordinator, option_key, default_value, name=None, *, unit="min", icon="mdi:timer", device_class=None):
        super().__init__(coordinator)
        self._option_key = option_key
        self._default = default_value
        # unique id mirrors other sensors: <entry_id>_<key>
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{option_key}"
        self._attr_translation_key = option_key
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        # Keep the option to pass a human-friendly fallback name; translations in
        # strings.json still provide canonical names when available.
        super().__init__(coordinator, name)

    @property
    def native_value(self):
        try:
            # Prefer persisted options, then entry.data, then default
            val = None
            if getattr(self.coordinator, "entry", None):
                val = (self.coordinator.entry.options or {}).get(self._option_key)
                if val is None:
                    val = (self.coordinator.entry.data or {}).get(self._option_key)
            if val is None:
                return int(self._default)
            return int(val)
        except Exception:
            return int(self._default)