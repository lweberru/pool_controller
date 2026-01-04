from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PoolStatusSensor(coordinator),
        PoolChemSensor(coordinator, "ph_val", "pH-Wert", None),
        PoolChemSensor(coordinator, "chlor_val", "Chlorgehalt", "mV"),
        PoolChemSensor(coordinator, "ph_minus_g", "Ph- Aktion", "g"),
        PoolChemSensor(coordinator, "chlor_spoons", "Chlor Aktion", "Löffel"),
        PoolTimeSensor(coordinator, "next_event", "Nächster Event Start")
    ]
    async_add_entities(entities)

class PoolBaseSensor(SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator): self.coordinator = coordinator
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class PoolStatusSensor(PoolBaseSensor):
    _attr_name = "Betriebsstatus"
    @property
    def native_value(self):
        if self.coordinator.data.get("is_paused"): return "Pause"
        return "Normal"

class PoolChemSensor(PoolBaseSensor):
    def __init__(self, coordinator, key, name, unit):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)

class PoolTimeSensor(PoolBaseSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)