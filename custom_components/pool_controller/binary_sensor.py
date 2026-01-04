from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PoolWEHolidaySensor(coordinator),
        PoolBinaryState(coordinator, "frost_danger", "Frostgefahr", BinarySensorDeviceClass.COLD)
    ])

class PoolBinaryState(BinarySensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, key, name, device_class):
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def is_on(self): return self.coordinator.data.get(self._key)
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class PoolWEHolidaySensor(PoolBinaryState):
    def __init__(self, coordinator):
        super().__init__(coordinator, "is_we_holiday", "Wochenende oder Feiertag", None)
        self._attr_icon = "mdi:calendar-star"