from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN, MANUFACTURER, CONF_MAIN_SWITCH, CONF_PUMP_SWITCH, CONF_AUX_HEATING_SWITCH
from .const import CONF_DEMO_MODE

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [PoolMainSwitch(coordinator), PoolPumpSwitch(coordinator)]
    if entry.data.get(CONF_AUX_HEATING_SWITCH):
        entities.append(PoolAuxSwitch(coordinator))
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

    def _merged_conf(self):
        return {**(self.coordinator.entry.data or {}), **(self.coordinator.entry.options or {})}

    def _resolved_switch(self, key: str, fallback_key: str | None = None) -> str | None:
        conf = self._merged_conf()
        entity_id = self.coordinator._resolve_external_actuator_entity(conf, key)
        if not entity_id and fallback_key:
            entity_id = self.coordinator._resolve_external_actuator_entity(conf, fallback_key)
        return entity_id
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
        entity_id = self._resolved_switch(CONF_MAIN_SWITCH)
        if entity_id:
            await self.hass.services.async_call("switch", "turn_on", {"entity_id": entity_id})
    async def async_turn_off(self, **kwargs):
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        # don't turn off main while bathing
        if self.coordinator.data.get("is_bathing"):
            return
        if demo:
            return
        entity_id = self._resolved_switch(CONF_MAIN_SWITCH)
        if entity_id:
            await self.hass.services.async_call("switch", "turn_off", {"entity_id": entity_id})


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
        entity_id = self._resolved_switch(CONF_PUMP_SWITCH, fallback_key=CONF_MAIN_SWITCH)
        if entity_id:
            await self.hass.services.async_call("switch", "turn_on", {"entity_id": entity_id})

    async def async_turn_off(self, **kwargs):
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        # don't turn off pump while bathing
        if self.coordinator.data.get("is_bathing"):
            return
        if demo:
            return
        entity_id = self._resolved_switch(CONF_PUMP_SWITCH, fallback_key=CONF_MAIN_SWITCH)
        if entity_id:
            await self.hass.services.async_call("switch", "turn_off", {"entity_id": entity_id})

class PoolAuxSwitch(PoolBaseSwitch):
    _attr_translation_key = "aux"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_aux"

    @property
    def is_on(self):
        aux_switch_id = self._resolved_switch(CONF_AUX_HEATING_SWITCH)
        if not aux_switch_id:
            return False
        st = self.coordinator.hass.states.get(aux_switch_id)
        return bool(st and st.state == "on")

    async def async_turn_on(self, **kwargs):
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        if demo:
            return
        aux_switch_id = self._resolved_switch(CONF_AUX_HEATING_SWITCH)
        if aux_switch_id:
            await self.hass.services.async_call("switch", "turn_on", {"entity_id": aux_switch_id})

    async def async_turn_off(self, **kwargs):
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        if demo:
            return
        aux_switch_id = self._resolved_switch(CONF_AUX_HEATING_SWITCH)
        if aux_switch_id:
            await self.hass.services.async_call("switch", "turn_off", {"entity_id": aux_switch_id})

class PoolAuxAllowedSwitch(PoolBaseSwitch):
    _attr_translation_key = "aux_allowed"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_aux_allowed"
    @property
    def is_on(self):
        # Zeigt Master-Enable-Status, nicht den physischen Schalter
        return self.coordinator.aux_allowed
    async def async_turn_on(self, **kwargs):
        # Aktiviere Master-Enable für Zusatzheizung
        self.coordinator.aux_allowed = True
        self.coordinator.aux_enabled = True
        await self.coordinator.async_request_refresh()
    async def async_turn_off(self, **kwargs):
        # Deaktiviere Master-Enable und schalte physischen Schalter sofort aus
        self.coordinator.aux_allowed = False
        self.coordinator.aux_enabled = False
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)
        aux_switch_id = self._resolved_switch(CONF_AUX_HEATING_SWITCH)
        if not demo and aux_switch_id:
            await self.hass.services.async_call("switch", "turn_off", {"entity_id": aux_switch_id})
        await self.coordinator.async_request_refresh()
