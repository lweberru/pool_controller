from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN, MANUFACTURER, CONF_MAIN_SWITCH, CONF_AUX_HEATING_SWITCH

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PoolMainSwitch(coordinator), PoolBathingSwitch(coordinator)])

class PoolBaseSwitch(SwitchEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator): self.coordinator = coordinator
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class PoolMainSwitch(PoolBaseSwitch):
    _attr_name = "Hauptschalter"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_main_sw"
    @property
    def is_on(self): return self.coordinator.data.get("should_main_on")
    async def async_turn_on(self, **kwargs):
        if not self.coordinator.demo_mode:
            await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.coordinator.entry.data.get(CONF_MAIN_SWITCH)})

class PoolBathingSwitch(PoolBaseSwitch):
    _attr_name = "Bade-Modus"
    _attr_icon = "mdi:pool"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bathing_sw"
    @property
    def is_on(self): return self.coordinator.is_bathing
    async def async_turn_on(self, **kwargs): self.coordinator.is_bathing = True
    async def async_turn_off(self, **kwargs): self.coordinator.is_bathing = False