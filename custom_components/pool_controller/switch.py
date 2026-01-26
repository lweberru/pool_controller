from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN, MANUFACTURER, CONF_MAIN_SWITCH, CONF_PUMP_SWITCH, CONF_AUX_HEATING_SWITCH
from .const import CONF_DEMO_MODE

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [PoolMainSwitch(coordinator), PoolPumpSwitch(coordinator)]
    if entry.data.get(CONF_AUX_HEATING_SWITCH):
        entities.append(PoolAuxAllowedSwitch(coordinator))
    async_add_entities(entities)

class PoolBaseSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, name=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        # Optional human-friendly fallback name when translations/registry
        # do not provide a translation_key/original_name yet.
        if name:
            self._attr_name = name
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class PoolMainSwitch(PoolBaseSwitch):
    _attr_translation_key = "main"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_main"
        # Fallback readable name while translations load
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


class PoolPumpSwitch(PoolBaseSwitch):
    _attr_translation_key = "pump"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pump"

    @property
    def is_on(self):
        return self.coordinator.data.get("should_pump_on")

    async def async_turn_on(self, **kwargs):
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        if demo:
            return
        entity_id = self.coordinator.entry.data.get(CONF_PUMP_SWITCH) or self.coordinator.entry.data.get(CONF_MAIN_SWITCH)
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": entity_id})

    async def async_turn_off(self, **kwargs):
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        # don't turn off pump while bathing
        if self.coordinator.data.get("is_bathing"):
            return
        if demo:
            return
        entity_id = self.coordinator.entry.data.get(CONF_PUMP_SWITCH) or self.coordinator.entry.data.get(CONF_MAIN_SWITCH)
        await self.hass.services.async_call("switch", "turn_off", {"entity_id": entity_id})

class PoolAuxAllowedSwitch(PoolBaseSwitch):
    _attr_translation_key = "aux_allowed"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        entry_id = coordinator.entry.entry_id
        new_uid = f"{entry_id}_aux_allowed"
        old_uid = f"{entry_id}_aux"
        try:
            ent_reg = er.async_get(coordinator.hass)
            old_entity_id = ent_reg.async_get_entity_id("switch", DOMAIN, old_uid)
            new_entity_id = ent_reg.async_get_entity_id("switch", DOMAIN, new_uid)
        except Exception:
            old_entity_id = None
            new_entity_id = None
        # Prefer the new unique_id, but keep the old one if it's the only existing registry entry
        # to avoid creating duplicate entities during migration.
        self._attr_unique_id = old_uid if (old_entity_id and not new_entity_id) else new_uid
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
