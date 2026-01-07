from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PoolBinary(coordinator, "is_we_holiday", "Wochenende oder Feiertag", None),
        PoolBinary(coordinator, "frost_danger", "Frostgefahr", BinarySensorDeviceClass.COLD),
        # Derived / template-like binary sensors provided by the integration
        PoolBinary(coordinator, "is_quick_chlor", "Stoßchlorung aktiv", None),
        PoolBinary(coordinator, "is_paused", "Pausiert", None),
        PoolBinary(coordinator, "is_bathing", "Baden aktiv", None),
        PoolBinary(coordinator, "filter_active", "Filter aktiv", None),
        PoolBinary(coordinator, "in_quiet", "Ruhemodus aktiv", None),
        PoolBinary(coordinator, "pv_allows", "PV Überschuss verfügbar", None),
        PoolBinary(coordinator, "should_main_on", "Hauptstrom erforderlich", None),
        PoolBinary(coordinator, "low_chlor", "Niedriger Chlorwert", None),
        PoolBinary(coordinator, "ph_alert", "pH außerhalb Bereich", None),
        PoolBinary(coordinator, "tds_high", "TDS zu hoch", BinarySensorDeviceClass.PROBLEM),
    ])

class PoolBinary(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, key, name, d_class):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._key = key
        self._attr_translation_key = key
        self._attr_device_class = d_class
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}
    @property
    def is_on(self):
        # Direct mapping if coordinator provides the key
        data = self.coordinator.data
        if self._key in data:
            return bool(data.get(self._key))
        # Derived checks
        if self._key == "low_chlor":
            val = data.get("chlor_val")
            return val is not None and float(val) < 600
        if self._key == "ph_alert":
            val = data.get("ph_val")
            return val is not None and (float(val) < 7.1 or float(val) > 7.4)
        return False