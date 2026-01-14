from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        Bath60Button(coordinator),
        Filter30Button(coordinator),
        Chlorine5Button(coordinator),
        Pause60Button(coordinator),
    ])

class PoolButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, name=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        # Optional human-friendly fallback name (used if translations/registry
        # don't provide a translation_key/original_name yet).
        if name:
            self._attr_name = name
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class Pause60Button(PoolButton):
    _attr_translation_key = "pause_60"
    _attr_icon = "mdi:pause-circle"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause_60"
    async def async_press(self):
        await self.coordinator.activate_pause(minutes=60)
        await self.coordinator.async_request_refresh()
class Bath60Button(PoolButton):
    _attr_translation_key = "bath_60"
    _attr_icon = "mdi:pool"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bath_60"
    async def async_press(self):
        await self.coordinator.activate_manual_timer(timer_type="bathing", minutes=60)
        await self.coordinator.async_request_refresh()
class Filter30Button(PoolButton):
    _attr_translation_key = "filter_30"
    _attr_icon = "mdi:rotate-right"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_filter_30"
    async def async_press(self):
        await self.coordinator.activate_manual_timer(timer_type="filter", minutes=30)
        await self.coordinator.async_request_refresh()


class Chlorine5Button(PoolButton):
    _attr_translation_key = "chlorine_5"
    _attr_icon = "mdi:fan"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_chlorine_5"
    async def async_press(self):
        await self.coordinator.activate_manual_timer(timer_type="chlorine", minutes=5)
        await self.coordinator.async_request_refresh()