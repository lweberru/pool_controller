from homeassistant.components.binary_sensor import BinarySensorEntity

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PoolWEHolidaySensor(coordinator)])

class PoolWEHolidaySensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Wochenende oder Feiertag"
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_we_holiday"
    @property
    def is_on(self): return self.coordinator.data.get("is_we_holiday")
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name")}