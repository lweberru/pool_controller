import logging
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN, CONF_MAIN_SWITCH, CONF_AUX_HEATING_SWITCH

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PoolMainSwitch(coordinator),
        PoolAuxHeatingSwitch(coordinator),
        PoolBathingModeSwitch(coordinator),
        PoolPauseSwitch(coordinator), # Neuer Pausen-Timer-Schalter
        PoolDemoModeSwitch(coordinator)
    ])

class PoolBaseSwitch(SwitchEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_has_entity_name = True

    async def async_execute_hardware(self, entity_id, action):
        if self.coordinator.demo_mode:
            _LOGGER.info("DEMO: %s -> %s", entity_id, action)
            return
        if entity_id:
            await self.hass.services.async_call("switch", f"turn_{action}", {"entity_id": entity_id})

class PoolPauseSwitch(PoolBaseSwitch):
    """Pausiert den Pool für 30 Minuten."""
    _attr_name = "Whirlpool Pause (30 min)"
    _attr_icon = "mdi:pause-circle"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause_switch"

    @property
    def is_on(self):
        return self.coordinator.data.get("is_paused", False)

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_pause(30)

    async def async_turn_off(self, **kwargs):
        self.coordinator.pause_until = None
        await self.coordinator.async_request_refresh()

class PoolMainSwitch(PoolBaseSwitch):
    _attr_name = "Hauptversorgung"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_main_switch"
    @property
    def is_on(self): return self.coordinator.data.get("should_main_on")
    async def async_turn_on(self, **kwargs): await self.async_execute_hardware(self.coordinator.entry.data.get(CONF_MAIN_SWITCH), "on")
    async def async_turn_off(self, **kwargs): await self.async_execute_hardware(self.coordinator.entry.data.get(CONF_MAIN_SWITCH), "off")

class PoolAuxHeatingSwitch(PoolBaseSwitch):
    _attr_name = "Zusatzheizung"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_aux_switch"
    @property
    def is_on(self): return self.coordinator.data.get("should_aux_on")
    async def async_turn_on(self, **kwargs): await self.async_execute_hardware(self.coordinator.entry.data.get(CONF_AUX_HEATING_SWITCH), "on")
    async def async_turn_off(self, **kwargs): await self.async_execute_hardware(self.coordinator.entry.data.get(CONF_AUX_HEATING_SWITCH), "off")

class PoolBathingModeSwitch(PoolBaseSwitch):
    _attr_name = "Bade-Modus"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bathing_mode"
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
        self._attr_unique_id = f"{coordinator.entry.entry_id}_demo_toggle"
    @property
    def is_on(self): return not self.coordinator.demo_mode
    async def async_turn_on(self, **kwargs): self.coordinator.demo_mode = False
    async def async_turn_off(self, **kwargs): self.coordinator.demo_mode = True