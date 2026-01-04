from homeassistant.components.button import ButtonEntity
from homeassistant.util import dt as dt_util
from datetime import timedelta
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([QuickChlorineButton(coordinator), PauseButton(coordinator)])

class PoolButton(ButtonEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator): self.coordinator = coordinator
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class QuickChlorineButton(PoolButton):
    _attr_name = "Kurz Chloren"
    _attr_unique_id = "quick_chlor_btn"
    _attr_icon = "mdi:fan"
    async def async_press(self):
        self.coordinator.quick_chlorine_until = dt_util.now() + timedelta(minutes=5)
        await self.coordinator.async_request_refresh()

class PauseButton(PoolButton):
    _attr_name = "Pausieren"
    _attr_unique_id = "pause_btn"
    _attr_icon = "mdi:pause-circle"
    async def async_press(self):
        self.coordinator.pause_until = dt_util.now() + timedelta(minutes=30)
        await self.coordinator.async_request_refresh()