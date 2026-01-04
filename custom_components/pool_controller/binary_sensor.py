from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PoolBinarySensor(coordinator, "frost_danger", "Frostgefahr", BinarySensorDeviceClass.COLD),
        PoolBinarySensor(coordinator, "is_quiet_time", "Ruhezeit", None),
        PoolBinarySensor(coordinator, "preheat_active", "Aufheiz-Planung", BinarySensorDeviceClass.HEAT),
        PoolBinarySensor(coordinator, "is_holiday", "Feiertag", None)
    ])

class PoolBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, data_key, name, device_class):
        self.coordinator = coordinator
        self._data_key = data_key
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{data_key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.data.get("name", "Whirlpool"),
            manufacturer=MANUFACTURER,
        )

    @property
    def is_on(self):
        return self.coordinator.data.get(self._data_key, False)