from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, MANUFACTURER, CONF_PH_SENSOR, CONF_CHLORINE_SENSOR, CONF_SALT_SENSOR

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [PoolStatusSensor(coordinator), HeatUpTimeSensor(coordinator), PoolTDSSensor(coordinator)]
    
    mapping = {CONF_PH_SENSOR: "pH-Wert", CONF_CHLORINE_SENSOR: "Chlorgehalt", CONF_SALT_SENSOR: "Salzgehalt"}
    for key, label in mapping.items():
        if entry.data.get(key):
            entities.append(PoolDataProxySensor(coordinator, key, label))
    
    async_add_entities(entities)

class PoolBaseSensor(SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator):
        self.coordinator = coordinator
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.data.get("name", "Whirlpool"),
            manufacturer=MANUFACTURER,
        )

class PoolStatusSensor(PoolBaseSensor):
    _attr_name = "Betriebsstatus"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_status"
    @property
    def native_value(self):
        if self.coordinator.data.get("is_paused"): return "Pause"
        if self.coordinator.data.get("frost_danger"): return "Frostschutz"
        return "Bereit"

class HeatUpTimeSensor(PoolBaseSensor):
    _attr_name = "Aufheizzeit"
    _attr_native_unit_of_measurement = "min"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_heat_time"
    @property
    def native_value(self): return self.coordinator.data.get("heat_up_time_mins")

class PoolTDSSensor(PoolBaseSensor):
    _attr_name = "TDS Wert"
    _attr_native_unit_of_measurement = "ppm"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_tds"
    @property
    def native_value(self): return self.coordinator.data.get("tds_value")

class PoolDataProxySensor(PoolBaseSensor):
    def __init__(self, coordinator, config_key, name):
        super().__init__(coordinator)
        self._config_key = config_key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{config_key}"
    @property
    def native_value(self):
        state = self.hass.states.get(self.coordinator.entry.data.get(self._config_key))
        return state.state if state else None