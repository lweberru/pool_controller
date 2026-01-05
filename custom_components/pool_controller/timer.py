from __future__ import annotations

from datetime import timedelta
from typing import Optional

from homeassistant.components.timer import TimerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PoolPauseTimer(coordinator),
        PoolFilterTimer(coordinator),
        PoolBathingTimer(coordinator),
    ])


class PoolTimerBase(CoordinatorEntity, TimerEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key: str, name: str):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}_timer"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.data.get("name"), "manufacturer": MANUFACTURER}

    @property
    def duration(self) -> Optional[timedelta]:
        # Return the configured duration for display (optional)
        return None

    @property
    def remaining(self) -> Optional[timedelta]:
        # Derived from coordinator timestamps
        ts = self._get_timestamp()
        if not ts:
            return None
        rem = ts - dt_util.now()
        return rem if rem.total_seconds() > 0 else timedelta(seconds=0)

    @property
    def is_active(self) -> bool:
        ts = self._get_timestamp()
        return ts is not None and dt_util.now() < ts

    def _get_timestamp(self) -> Optional[dt_util.datetime]:
        raise NotImplementedError()

    async def async_start(self, duration: Optional[timedelta] = None) -> None:
        raise NotImplementedError()

    async def async_cancel(self) -> None:
        raise NotImplementedError()

    async def async_finish(self) -> None:
        # Usually called when timer naturally finishes — ensure coordinator is refreshed
        await self.coordinator.async_request_refresh()


class PoolPauseTimer(PoolTimerBase):
    def __init__(self, coordinator):
        super().__init__(coordinator, "pause", "Pause Timer")

    def _get_timestamp(self):
        return self.coordinator.pause_until

    @property
    def duration(self) -> Optional[timedelta]:
        # Not a fixed duration — cannot show a single duration
        return None

    async def async_start(self, duration: Optional[timedelta] = None) -> None:
        minutes = int(duration.total_seconds() / 60) if duration else 30
        await self.coordinator.activate_pause(minutes=minutes)
        await self.coordinator.async_request_refresh()

    async def async_cancel(self) -> None:
        await self.coordinator.activate_pause(minutes=0)
        await self.coordinator.async_request_refresh()


class PoolFilterTimer(PoolTimerBase):
    def __init__(self, coordinator):
        super().__init__(coordinator, "filter", "Filter Timer")

    def _get_timestamp(self):
        return getattr(self.coordinator, "filter_until", None)

    @property
    def duration(self) -> Optional[timedelta]:
        return timedelta(minutes=getattr(self.coordinator, "filter_minutes", 30))

    async def async_start(self, duration: Optional[timedelta] = None) -> None:
        minutes = int(duration.total_seconds() / 60) if duration else int(self.coordinator.entry.options.get("filter_minutes", getattr(self.coordinator, "filter_minutes", 30)))
        await self.coordinator.activate_filter(minutes=minutes)
        await self.coordinator.async_request_refresh()

    async def async_cancel(self) -> None:
        await self.coordinator.deactivate_filter()
        await self.coordinator.async_request_refresh()


class PoolBathingTimer(PoolTimerBase):
    def __init__(self, coordinator):
        super().__init__(coordinator, "bathing", "Bathing Timer")

    def _get_timestamp(self):
        return self.coordinator.bathing_until

    @property
    def duration(self) -> Optional[timedelta]:
        return timedelta(minutes=int(self.coordinator.entry.options.get("bathing_minutes", getattr(self.coordinator, "filter_minutes", 60))))

    async def async_start(self, duration: Optional[timedelta] = None) -> None:
        minutes = int(duration.total_seconds() / 60) if duration else int(self.coordinator.entry.options.get("bathing_minutes", 60))
        await self.coordinator.activate_bathing(minutes=minutes)
        await self.coordinator.async_request_refresh()

    async def async_cancel(self) -> None:
        await self.coordinator.deactivate_bathing()
        await self.coordinator.async_request_refresh()
