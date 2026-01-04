import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from .const import (
    DOMAIN, 
    MANUFACTURER, 
    CONF_PH_SENSOR, 
    CONF_CHLORINE_SENSOR, 
    CONF_SALT_SENSOR,
    CONF_TDS_SENSOR
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setzt die Sensor-Plattform auf."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        PoolStatusSensor(coordinator),
        HeatUpTimeSensor(coordinator),
        PoolTDSSensor(coordinator),
        # Chemie-Dosierung
        PoolActionSensor(coordinator, "ph_minus_g", "Ph- Aktion", "g", "mdi:pill"),
        PoolActionSensor(coordinator, "ph_plus_g", "Ph+ Aktion", "g", "mdi:pill"),
        PoolActionSensor(coordinator, "chlor_spoons", "Chlor Aktion", "Löffel", "mdi:spoon-sugar"),
        # Kalender-Informationen
        PoolTimeSensor(coordinator, "next_event", "Nächster Event Start"),
        PoolTimeSensor(coordinator, "preheat_start", "Nächster Start (Heizung)")
    ]

    # Proxy-Sensoren für die Ist-Werte vom ESP32 (mit Rundung)
    if entry.data.get(CONF_PH_SENSOR):
        entities.append(PoolDataProxySensor(coordinator, CONF_PH_SENSOR, "pH-Wert", 2))
    if entry.data.get(CONF_CHLORINE_SENSOR):
        entities.append(PoolDataProxySensor(coordinator, CONF_CHLORINE_SENSOR, "Chlorgehalt", 0))
    if entry.data.get(CONF_SALT_SENSOR):
        entities.append(PoolDataProxySensor(coordinator, CONF_SALT_SENSOR, "Salzgehalt", 1, "g/L"))

    async_add_entities(entities)

class PoolBaseSensor(SensorEntity):
    """Basis-Klasse mit Device Info für alle Pool-Sensoren."""
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.data.get("name", "Whirlpool"),
            manufacturer=MANUFACTURER,
            model="Advanced Controller v1",
            sw_version="1.0.7",
        )

class PoolStatusSensor(PoolBaseSensor):
    """Zeigt den aktuellen Text-Status des Pools."""
    _attr_name = "Betriebsstatus"
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_status"

    @property
    def native_value(self):
        if self.coordinator.data.get("is_quick_chlorine"): return "Stoßchlorung aktiv"
        if self.coordinator.data.get("is_paused"): return "Pause"
        if self.coordinator.data.get("frost_danger"): return "Frostschutz"
        return "Normalbetrieb"

class HeatUpTimeSensor(PoolBaseSensor):
    """Berechnete Aufheizzeit."""
    _attr_name = "Aufheizzeit"
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_heat_time"

    @property
    def native_value(self):
        return self.coordinator.data.get("heat_up_time_mins")

class PoolTDSSensor(PoolBaseSensor):
    """Berechneter TDS Wert aus Leitfähigkeit."""
    _attr_name = "TDS Wert"
    _attr_native_unit_of_measurement = "ppm"
    _attr_icon = "mdi:water-opacity"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_tds_calc"

    @property
    def native_value(self):
        return self.coordinator.data.get("tds_value")

class PoolActionSensor(PoolBaseSensor):
    """Sensoren für Dosierempfehlungen (g, Löffel)."""
    def __init__(self, coordinator, key, name, unit, icon):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

class PoolTimeSensor(PoolBaseSensor):
    """Sensoren für Zeitstempel aus dem Kalender."""
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

class PoolDataProxySensor(PoolBaseSensor):
    """Spiegelt externe Sensoren (pH, Chlor) mit sauberer Rundung."""
    def __init__(self, coordinator, config_key, name, precision, unit=None):
        super().__init__(coordinator)
        self._config_key = config_key
        self._precision = precision
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{coordinator.entry.entry_id}_proxy_{config_key}"

    @property
    def native_value(self):
        entity_id = self.coordinator.entry.data.get(self._config_key)
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                val = float(state.state)
                return round(val, self._precision) if self._precision > 0 else int(round(val))
            except ValueError:
                return state.state
        return None