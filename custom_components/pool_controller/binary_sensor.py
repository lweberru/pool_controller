import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setzt die Binary-Sensor-Plattform auf."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Wir erstellen eine Liste von Sensoren basierend auf den Coordinator-Daten
    entities = [
        PoolBinarySensor(coordinator, "frost_danger", "Frostgefahr", BinarySensorDeviceClass.COLD, "mdi:snowflake-alert"),
        PoolBinarySensor(coordinator, "is_quiet_time", "Ruhezeit aktiv", None, "mdi:sleep"),
        PoolBinarySensor(coordinator, "preheat_active", "Aufheiz-Planung", BinarySensorDeviceClass.HEAT, "mdi:calendar-clock"),
        PoolBinarySensor(coordinator, "filter_needed", "Filter-Zyklus fällig", BinarySensorDeviceClass.RUNNING, "mdi:filter-cog"),
        PoolBinarySensor(coordinator, "is_holiday", "Feiertag", None, "mdi:calendar-star"),
        PoolBinarySensor(coordinator, "should_main_on", "Hauptversorgung angefordert", BinarySensorDeviceClass.POWER, "mdi:power-cycle"),
    ]
    
    async_add_entities(entities)

class PoolBinarySensor(BinarySensorEntity):
    """Repräsentiert einen binären Zustand des Whirlpools."""

    def __init__(self, coordinator, data_key, name, device_class=None, icon=None):
        """Initialisierung des Sensors."""
        self.coordinator = coordinator
        self._data_key = data_key
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{data_key}"
        self._attr_has_entity_name = True

    @property
    def is_on(self) -> bool:
        """Gibt den Status aus dem Coordinator zurück."""
        return self.coordinator.data.get(self._data_key, False)

    @property
    def extra_state_attributes(self):
        """Zusätzliche Infos (z.B. ob der Demo-Modus aktiv ist)."""
        return {
            "demo_mode": self.coordinator.demo_mode
        }