from homeassistant.components.button import ButtonEntity
from homeassistant.util import dt as dt_util
from datetime import timedelta
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        QuickChlorineButton(coordinator),
        PauseButton(coordinator),
        BathNowButton(coordinator),
        FilterNowButton(coordinator),
    ])

class PoolButton(ButtonEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator): self.coordinator = coordinator
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class QuickChlorineButton(PoolButton):
    _attr_translation_key = "quick_chlor_btn"
    _attr_unique_id = "quick_chlor_btn"
    _attr_icon = "mdi:fan"
    async def async_press(self):
        await self.coordinator.activate_quick_chlorine(minutes=5)
        await self.coordinator.async_request_refresh()

class PauseButton(PoolButton):
    _attr_translation_key = "pause_btn"
    _attr_unique_id = "pause_btn"
    _attr_icon = "mdi:pause-circle"
    async def async_press(self):
        await self.coordinator.activate_pause(minutes=30)
        await self.coordinator.async_request_refresh()

class BathNowButton(PoolButton):
    _attr_translation_key = "bath_now"
    _attr_unique_id = "bath_now"
    _attr_icon = "mdi:pool"
    async def async_press(self):
        minutes = int(self.coordinator.entry.options.get("bathing_minutes", 60))
        await self.coordinator.activate_bathing(minutes=minutes)
        await self.coordinator.async_request_refresh()

class FilterNowButton(PoolButton):
    _attr_translation_key = "filter_now"
    _attr_unique_id = "filter_now"
    _attr_icon = "mdi:rotate-right"
    async def async_press(self):
        minutes = int(self.coordinator.entry.options.get("filter_minutes", 30))
        await self.coordinator.activate_filter(minutes=minutes)
        await self.coordinator.async_request_refresh()