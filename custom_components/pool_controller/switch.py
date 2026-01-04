from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, MANUFACTURER, CONF_MAIN_SWITCH, CONF_AUX_HEATING_SWITCH

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PoolMainSwitch(coordinator), PoolAuxHeatingSwitch(coordinator),
        PoolBathingModeSwitch(coordinator), PoolPauseSwitch(coordinator), PoolDemoModeSwitch(coordinator)
    ])

class PoolBaseSwitch(SwitchEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator):
        self.coordinator = coordinator
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.data.get("name", "Whirlpool"),
            manufacturer=MANUFACTURER,
        )
    async def async_execute_hardware(self, entity_id, action):
        if self.coordinator.demo_mode: return
        await self.hass.services.async_call("switch", f"turn_{action}", {"entity_id": entity_id})

class PoolMainSwitch(PoolBaseSwitch):
    _attr_name = "Hauptversorgung"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_main_sw"
    @property
    def is_on(self): return self.coordinator.data.get("should_main_on")
    async def async_turn_on(self, **kwargs): await self.async_execute_hardware(self.coordinator.entry.data.get(CONF_MAIN_SWITCH), "on")
    async def async_turn_off(self, **kwargs): await self.async_execute_hardware(self.coordinator.entry.data.get(CONF_MAIN_SWITCH), "off")

class PoolPauseSwitch(PoolBaseSwitch):
    _attr_name = "Pause (30 min)"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause_sw"
    @property
    def is_on(self): return self.coordinator.data.get("is_paused")
    async def async_turn_on(self, **kwargs): await self.coordinator.set_pause(30)
    async def async_turn_off(self, **kwargs): 
        self.coordinator.pause_until = None
        await self.coordinator.async_request_refresh()

class PoolBathingModeSwitch(PoolBaseSwitch):
    _attr_name = "Bade-Modus"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bath_sw"
    @property
    def is_on(self): return self.coordinator.is_bathing
    async def async_turn_on(self, **kwargs): 
        self.coordinator.is_bathing = True
        await self.coordinator.async_request_refresh()
    async def async_turn_off(self, **kwargs): 
        self.coordinator.is_bathing = False
        await self.coordinator.async_request_refresh()

class PoolDemoModeSwitch(PoolBaseSwitch):
    _attr_name = "Live-Steuerung Aktiv"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_demo_sw"
    @property
    def is_on(self): return not self.coordinator.demo_mode
    async def async_turn_on(self, **kwargs): self.coordinator.demo_mode = False
    async def async_turn_off(self, **kwargs): self.coordinator.demo_mode = True

class PoolAuxHeatingSwitch(PoolBaseSwitch):
    _attr_name = "Zusatzheizung"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_aux_sw"
    @property
    def is_on(self): return self.coordinator.data.get("should_aux_on")
    async def async_turn_on(self, **kwargs): await self.async_execute_hardware(self.coordinator.entry.data.get(CONF_AUX_HEATING_SWITCH), "on")
    async def async_turn_off(self, **kwargs): await self.async_execute_hardware(self.coordinator.entry.data.get(CONF_AUX_HEATING_SWITCH), "off")