import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .const import DOMAIN, CONF_PH_SENSOR, CONF_CHLORINE_SENSOR, CONF_SALT_SENSOR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        PoolStatusSensor(coordinator),
        HeatUpTimeSensor(coordinator),
        PoolTDSSensor(coordinator), # Der neue berechnete TDS Sensor
    ]

    if entry.data.get(CONF_PH_SENSOR):
        entities.append(PoolDataProxySensor(coordinator, CONF_PH_SENSOR, "pH-Wert", "mdi:ph"))
    if entry.data.get(CONF_CHLORINE_SENSOR):
        entities.append(PoolDataProxySensor(coordinator, CONF_CHLORINE_SENSOR, "Chlorgehalt", "mdi:pool"))
    if entry.data.get(CONF_SALT_SENSOR):
        entities.append(PoolDataProxySensor(coordinator, CONF_SALT_SENSOR, "Salzgehalt", "mdi:shaker"))

    async_add_entities(entities)

class PoolTDSSensor(SensorEntity):
    """Berechneter TDS Wert."""
    _attr_name = "TDS Wert"
    _attr_native_unit_of_measurement = "ppm"
    _attr_icon = "mdi:water-opacity"

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_tds"
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        return self.coordinator.data.get("tds_value")

class PoolStatusSensor(SensorEntity):
    _attr_name = "Betriebsstatus"
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_status"
        self._attr_has_entity_name = True
    @property
    def state(self):
        if self.coordinator.data.get("is_paused"): return "Pause (30 min)"
        if self.coordinator.data.get("frost_danger"): return "Frostschutz"
        if self.coordinator.data.get("preheat_active"): return "Aufheizen für Termin"
        return "Bereit"

class HeatUpTimeSensor(SensorEntity):
    _attr_name = "Verbleibende Aufheizzeit"
    _attr_native_unit_of_measurement = "min"
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_heat_time"
        self._attr_has_entity_name = True
    @property
    def native_value(self): return self.coordinator.data.get("heat_up_time_mins")

class PoolDataProxySensor(SensorEntity):
    def __init__(self, coordinator, config_key, name, icon):
        self.coordinator = coordinator
        self._config_key = config_key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{config_key}"
        self._attr_has_entity_name = True
    @property
    def native_value(self):
        entity_id = self.coordinator.entry.data.get(self._config_key)
        state = self.coordinator.hass.states.get(entity_id)
        return state.state if state else None