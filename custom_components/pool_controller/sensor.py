from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PoolStatusSensor(coordinator),
        PoolChemSensor(coordinator, "ph_val", "pH-Wert", None, "mdi:ph"),
        PoolChemSensor(coordinator, "chlor_val", "Chlorgehalt", "mV", "mdi:pool"),
        PoolChemSensor(coordinator, "ph_minus_g", "Ph- Aktion", "g", "mdi:pill"),
        PoolChemSensor(coordinator, "ph_plus_g", "Ph+ Aktion", "g", "mdi:pill"),
        PoolChemSensor(coordinator, "chlor_spoons", "Chlor Aktion", "Löffel", "mdi:spoon-sugar"),
        PoolChemSensor(coordinator, "next_start_mins", "Nächster Start in", "min", "mdi:clock-start"),
        PoolTimeSensor(coordinator, "next_event", "Nächster Event Start")
    ]
    async_add_entities(entities)

class PoolBaseSensor(SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator): self.coordinator = coordinator
    @property
    def device_info(self): return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class PoolStatusSensor(PoolBaseSensor):
    _attr_translation_key = "status"
    @property
    def native_value(self):
        if self.coordinator.data.get("frost_danger"): return "frost_protection"
        if self.coordinator.data.get("is_paused"): return "paused"
        return "normal"

class PoolChemSensor(PoolBaseSensor):
    def __init__(self, coordinator, key, name, unit, icon):
        super().__init__(coordinator)
        self._key, self._attr_translation_key, self._attr_native_unit_of_measurement, self._attr_icon = key, key, unit, icon
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)

class PoolTimeSensor(PoolBaseSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._key, self._attr_translation_key = key, key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)