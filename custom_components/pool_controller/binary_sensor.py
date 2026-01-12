from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MANUFACTURER, CONF_ENABLE_AUX_HEATING, CONF_AUX_HEATING_SWITCH

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PoolBinary(coordinator, "maintenance_active", "Wartung aktiv", BinarySensorDeviceClass.PROBLEM),
        PoolBinary(coordinator, "is_we_holiday", "Wochenende oder Feiertag", None),
        PoolBinary(coordinator, "frost_danger", "Frostgefahr", BinarySensorDeviceClass.COLD),
        PoolBinary(coordinator, "frost_active", "Frostschutz aktiv", BinarySensorDeviceClass.COLD),
        # Derived / template-like binary sensors provided by the integration
        PoolBinary(coordinator, "in_quiet", "Ruhemodus aktiv", None),
        PoolBinary(coordinator, "pv_allows", "PV Überschuss verfügbar", None),
        PoolBinary(coordinator, "should_main_on", "Hauptstrom erforderlich", None),
        PoolBinary(coordinator, "should_pump_on", "Pumpe erforderlich", None),
        # Physical switch state mirrors (configured external switches)
        PoolBinary(coordinator, "main_switch_on", "Hauptschalter an", BinarySensorDeviceClass.POWER),
        PoolBinary(coordinator, "pump_switch_on", "Pumpe an", None),
        PoolBinary(coordinator, "aux_heating_switch_on", "Zusatzheizung an", BinarySensorDeviceClass.HEAT),
        # Indicates whether an auxiliary heater is configured for this controller
        PoolBinary(coordinator, "aux_present", "Zusatzheizung konfiguriert", None),
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
        if self._key == "aux_present":
            # Consider aux present if aux heating is enabled or an aux_heating_switch is configured
            merged = {**(self.coordinator.entry.data or {}), **(self.coordinator.entry.options or {})}
            try:
                if bool(merged.get(CONF_ENABLE_AUX_HEATING, False)):
                    return True
            except Exception:
                pass
            # Only count a configured aux switch as present if the referenced entity actually exists in hass.states
            try:
                aux_switch = merged.get(CONF_AUX_HEATING_SWITCH)
                if aux_switch and isinstance(aux_switch, str) and self.hass.states.get(aux_switch):
                    return True
            except Exception:
                pass
            return False
        return False