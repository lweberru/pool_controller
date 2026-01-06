from homeassistant.components.button import ButtonEntity
from homeassistant.util import dt as dt_util
from datetime import timedelta
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        QuickChlorineButton(coordinator),
        Pause30Button(coordinator),
        Pause60Button(coordinator),
        Pause120Button(coordinator),
        PauseStopButton(coordinator),
        Bath30Button(coordinator),
        Bath60Button(coordinator),
        Bath120Button(coordinator),
        BathStopButton(coordinator),
        Filter30Button(coordinator),
        Filter60Button(coordinator),
        Filter120Button(coordinator),
        FilterStopButton(coordinator),
    ])

class PoolButton(ButtonEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator): self.coordinator = coordinator
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

class QuickChlorineButton(PoolButton):
    _attr_translation_key = "quick_chlor_btn"
    _attr_icon = "mdi:fan"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_quick_chlor"
    async def async_press(self):
        await self.coordinator.activate_quick_chlorine(minutes=5)
        await self.coordinator.async_request_refresh()

# Pause-Buttons mit verschiedenen Dauern
class Pause30Button(PoolButton):
    _attr_translation_key = "pause_30"
    _attr_icon = "mdi:pause"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause_30"
    async def async_press(self):
        await self.coordinator.activate_pause(minutes=30)
        await self.coordinator.async_request_refresh()

class Pause60Button(PoolButton):
    _attr_translation_key = "pause_60"
    _attr_icon = "mdi:pause"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause_60"
    async def async_press(self):
        await self.coordinator.activate_pause(minutes=60)
        await self.coordinator.async_request_refresh()

class Pause120Button(PoolButton):
    _attr_translation_key = "pause_120"
    _attr_icon = "mdi:pause"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause_120"
    async def async_press(self):
        await self.coordinator.activate_pause(minutes=120)
        await self.coordinator.async_request_refresh()

class PauseStopButton(PoolButton):
    _attr_translation_key = "pause_stop"
    _attr_icon = "mdi:stop-circle"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause_stop"
    async def async_press(self):
        await self.coordinator.activate_pause(minutes=0)
        await self.coordinator.async_request_refresh()

class Bath30Button(PoolButton):
    _attr_translation_key = "bath_30"
    _attr_icon = "mdi:pool"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bath_30"
    async def async_press(self):
        await self.coordinator.activate_bathing(minutes=30)
        await self.coordinator.async_request_refresh()

# Bathing-Buttons mit verschiedenen Dauern
class Bath30Button(PoolButton):
    _attr_translation_key = "bath_30"
    _attr_icon = "mdi:pool"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bath_30"
    async def async_press(self):
        await self.coordinator.activate_bathing(minutes=30)
        await self.coordinator.async_request_refresh()

class Bath60Button(PoolButton):
    _attr_translation_key = "bath_60"
    _attr_icon = "mdi:pool"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bath_60"
    async def async_press(self):
        await self.coordinator.activate_bathing(minutes=60)
        await self.coordinator.async_request_refresh()

class Bath120Button(PoolButton):
    _attr_translation_key = "bath_120"
    _attr_icon = "mdi:pool"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bath_120"
    async def async_press(self):
        await self.coordinator.activate_bathing(minutes=120)
        await self.coordinator.async_request_refresh()

class BathStopButton(PoolButton):
    _attr_translation_key = "bath_stop"
    _attr_icon = "mdi:stop-circle"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_bath_stop"
    async def async_press(self):
        await self.coordinator.deactivate_bathing()
        await self.coordinator.async_request_refresh()

class Filter30Button(PoolButton):
    _attr_translation_key = "filter_30"
    _attr_icon = "mdi:rotate-right"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_filter_30"
    async def async_press(self):
        await self.coordinator.activate_filter(minutes=30)
        await self.coordinator.async_request_refresh()

# Filter-Buttons mit verschiedenen Dauern
class Filter30Button(PoolButton):
    _attr_translation_key = "filter_30"
    _attr_icon = "mdi:rotate-right"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_filter_30"
    async def async_press(self):
        await self.coordinator.activate_filter(minutes=30)
        await self.coordinator.async_request_refresh()

class Filter60Button(PoolButton):
    _attr_translation_key = "filter_60"
    _attr_icon = "mdi:rotate-right"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_filter_60"
    async def async_press(self):
        await self.coordinator.activate_filter(minutes=60)
        await self.coordinator.async_request_refresh()

class Filter120Button(PoolButton):
    _attr_translation_key = "filter_120"
    _attr_icon = "mdi:rotate-right"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_filter_120"
    async def async_press(self):
        await self.coordinator.activate_filter(minutes=120)
        await self.coordinator.async_request_refresh()

class FilterStopButton(PoolButton):
    _attr_translation_key = "filter_stop"
    _attr_icon = "mdi:stop-circle"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_filter_stop"
    async def async_press(self):
        await self.coordinator.deactivate_filter()
        await self.coordinator.async_request_refresh()