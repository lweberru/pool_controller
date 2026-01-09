from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PoolStatusSensor(coordinator),
        PoolChemSensor(coordinator, "ph_val", "pH-Wert", None, "mdi:ph"),
        PoolChemSensor(coordinator, "chlor_val", "Chlorgehalt", "mV", "mdi:pool"),
        PoolChemSensor(coordinator, "salt_val", "Salzgehalt", "g/L", "mdi:shaker"),
        PoolChemSensor(coordinator, "tds_val", "TDS", "ppm", "mdi:water-opacity"),
        PoolChemSensor(coordinator, "tds_water_change_liters", "TDS Wasserwechsel", "L", "mdi:water-sync"),
        PoolChemSensor(coordinator, "tds_water_change_percent", "TDS Wasserwechsel", "%", "mdi:water-percent"),
        PoolChemSensor(coordinator, "ph_minus_g", "Ph- Aktion", "g", "mdi:pill"),
        PoolChemSensor(coordinator, "ph_plus_g", "Ph+ Aktion", "g", "mdi:pill"),
        PoolChemSensor(coordinator, "chlor_spoons", "Chlor Aktion", "Löffel", "mdi:spoon-sugar"),
        PoolChemSensor(coordinator, "next_start_mins", "Nächster Start in", "min", "mdi:clock-start"),
        PoolTimeSensor(coordinator, "next_event", "Nächster Event Start")
    ]
    # Timer/Status sensors
    entities.extend([
        PoolTdsStatusSensor(coordinator),
        PoolTimerSensor(coordinator, "manual_timer_mins", "mdi:timer", kind="manual"),
        PoolTimerSensor(coordinator, "auto_filter_timer_mins", "mdi:timer-cog", kind="auto_filter"),
        PoolTimerSensor(coordinator, "pause_timer_mins", "mdi:pause-circle", kind="pause"),
        PoolChemSensor(coordinator, "next_filter_mins", "Nächster Filter in", "min", "mdi:clock-start"),
        PoolTimeSensor(coordinator, "next_event_end", "Nächster Event Ende"),
        PoolTextSensor(coordinator, "next_event_summary", "Nächster Event Name"),
    ])
    # Power sensors
    entities.extend([
        PoolPowerSensor(coordinator, "pv_power", "PV Power"),
        PoolPowerSensor(coordinator, "main_power", "Hauptpumpe Leistung"),
        PoolPowerSensor(coordinator, "aux_power", "Heizung Leistung"),
    ])
    async_add_entities(entities)

class PoolBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
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
    def __init__(self, coordinator, key, name, unit, icon):
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)

class PoolTimeSensor(PoolBaseSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
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
        super().__init__(coordinator)
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
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = key
        self._attr_icon = "mdi:calendar-text"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)


class PoolTimerSensor(PoolBaseSensor):
    _attr_native_unit_of_measurement = "min"
    _attr_state_class = SensorStateClass.MEASUREMENT

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
        try:
            return int(val) if val is not None else 0
        except Exception:
            return 0

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
        return {}