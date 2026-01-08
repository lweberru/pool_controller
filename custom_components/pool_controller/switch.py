from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MANUFACTURER, CONF_MAIN_SWITCH, CONF_AUX_HEATING_SWITCH
from .const import CONF_DEMO_MODE

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [PoolMainSwitch(coordinator)]
    if entry.data.get(CONF_AUX_HEATING_SWITCH):
        entities.append(PoolAuxSwitch(coordinator))
    async_add_entities(entities)

class PoolBaseSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class PoolMainSwitch(PoolBaseSwitch):
    _attr_translation_key = "main"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_main"
    @property
    def is_on(self):
        return self.coordinator.data.get("should_main_on")
    async def async_turn_on(self, **kwargs):
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        if demo:
            return
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.coordinator.entry.data.get(CONF_MAIN_SWITCH)})
    async def async_turn_off(self, **kwargs):
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        # don't turn off main while bathing
        if self.coordinator.data.get("is_bathing"):
            return
        if demo:
            return
        await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.coordinator.entry.data.get(CONF_MAIN_SWITCH)})

class PoolAuxSwitch(PoolBaseSwitch):
    _attr_translation_key = "aux"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_aux"
    @property
    def is_on(self):
        # Zeigt Master-Enable-Status, nicht den physischen Schalter
        return self.coordinator.aux_enabled
    async def async_turn_on(self, **kwargs):
        # Aktiviere Master-Enable für Zusatzheizung
        self.coordinator.aux_enabled = True
        await self.coordinator.async_request_refresh()
    async def async_turn_off(self, **kwargs):
        # Deaktiviere Master-Enable und schalte physischen Schalter sofort aus
        self.coordinator.aux_enabled = False
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        aux_switch_id = self.coordinator.entry.data.get(CONF_AUX_HEATING_SWITCH)
        if not demo and aux_switch_id:
            await self.hass.services.async_call("switch", "turn_off", {"entity_id": aux_switch_id})
        await self.coordinator.async_request_refresh()
