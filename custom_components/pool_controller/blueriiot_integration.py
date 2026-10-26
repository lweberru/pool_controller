"""Consume BlueRiiot Bluetooth entities without opening another BLE connection."""

from dataclasses import dataclass
from datetime import timedelta
import math

from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util


@dataclass(frozen=True, slots=True)
class IntegrationReading:
    temperature: float
    ph: float
    orp: float
    salt: float | None
    conductivity: float | None
    battery: float | None


class BlueRiiotIntegrationReader:
    """Resolve the selected device's stable entity unique IDs on every refresh."""

    def __init__(self, hass):
        self._hass = hass
        self.reading = None
        self.last_success = None
        self.last_error = None
        self.interval_minutes = 15
        self._connected = False

    def _entities(self, device_id):
        device = dr.async_get(self._hass).async_get(device_id)
        if device is None:
            return {}
        entries = [self._hass.config_entries.async_get_entry(eid) for eid in device.config_entries]
        prefixes = [f"{entry.unique_id}_" for entry in entries if entry and entry.domain == "blueriiot"]
        for entry in entries:
            if entry and entry.domain == "blueriiot":
                self.interval_minutes = int(entry.options.get("update_interval", 15))
        return {
            entity.unique_id[len(prefix):]: entity.entity_id
            for entity in er.async_entries_for_device(er.async_get(self._hass), device_id)
            if entity.platform == "blueriiot" and not entity.disabled_by
            for prefix in prefixes if entity.unique_id.startswith(prefix)
        }

    def _state(self, entities, key):
        state = self._hass.states.get(entities.get(key, ""))
        return state if state and state.state not in ("unknown", "unavailable", "") else None

    def _number(self, entities, key):
        state = self._state(entities, key)
        try:
            value = float(state.state) if state else None
            return value if value is not None and math.isfinite(value) else None
        except (TypeError, ValueError):
            return None

    async def async_read_if_due(self, device_id, minimum_interval, *, force=False, salt_divisor=18.0):
        """Read published states; only an explicit request presses the source button."""
        self.reading = None
        self.last_success = None
        self._connected = False
        entities = self._entities(device_id)
        if force:
            if not entities.get("refresh"):
                self.last_error = "source_refresh_unavailable"
                return None
            await self._hass.services.async_call(
                "button", "press", {"entity_id": entities["refresh"]}, blocking=True
            )
        last_success = self._state(entities, "last_success")
        self.last_success = dt_util.parse_datetime(last_success.state) if last_success else None
        connected = self._state(entities, "connected")
        self._connected = bool(connected and connected.state == "on")
        error = self._state(entities, "last_error")
        self.last_error = error.state if error else None
        temperature = self._number(entities, "temperature")
        ph = self._number(entities, "ph")
        orp = self._number(entities, "orp")
        if any(value is None for value in (temperature, ph, orp)):
            self.last_error = self.last_error or "source_measurements_unavailable"
            return None
        unit = self._state(entities, "temperature").attributes.get("unit_of_measurement")
        if unit == "°F":
            temperature = (temperature - 32) * 5 / 9
        elif unit == "K":
            temperature -= 273.15
        self.reading = IntegrationReading(
            temperature, ph, orp,
            self._number(entities, "salt"),
            self._number(entities, "conductivity"),
            self._number(entities, "battery"),
        )
        if not self.is_recently_reachable(minimum_interval):
            self.last_error = self.last_error or "source_measurements_stale"
        return self.reading

    def is_recently_reachable(self, maximum_age):
        """Respect the source's poll interval and connectivity, including stale data."""
        return bool(
            self._connected and self.reading and self.last_success
            and self.last_success.tzinfo is not None
            and timedelta(0) <= dt_util.utcnow() - self.last_success
            <= timedelta(minutes=max(30, self.interval_minutes * 2))
        )
