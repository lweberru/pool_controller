import logging
from datetime import timedelta, datetime
import asyncio
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from .const import *

_LOGGER = logging.getLogger(__name__)

class PoolControllerDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        self.entry = entry
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=30))
        self.target_temp = 38.0
        self.is_bathing = False
        self.last_filter_run = dt_util.now() - timedelta(hours=12)
        self.demo_mode = entry.data.get(CONF_DEMO_MODE, False)
        self.pause_until = None
        self.quick_chlorine_until = None # Timer für 5 Min Chloren

    async def _async_update_data(self):
        try:
            now = dt_util.now()
            
            # 1. Daten abrufen & Runden
            raw_water_temp = self._get_float_state(self.entry.data.get(CONF_TEMP_WATER))
            water_temp = round(raw_water_temp, 1) if raw_water_temp else None
            
            raw_ph = self._get_float_state(self.entry.data.get(CONF_PH_SENSOR))
            ph_val = round(raw_ph, 2) if raw_ph else None
            
            raw_chlor = self._get_float_state(self.entry.data.get(CONF_CHLORINE_SENSOR))
            chlor_val = round(raw_chlor, 0) if raw_chlor else None # mV oft ganzzahlig
            
            raw_salt = self._get_float_state(self.entry.data.get(CONF_SALT_SENSOR))
            salt_val = round(raw_salt, 1) if raw_salt else 0.0

            # 2. Chemie-Berechnung (Beispielwerte für 1000L)
            # Ziel pH: 7.2 | 10g PH- senkt um 0.1 pro 1000L
            vol = self.entry.data.get(CONF_WATER_VOLUME, 1000)
            ph_minus = round((ph_val - 7.2) * (vol / 1000) * 100, 0) if ph_val and ph_val > 7.2 else 0
            ph_plus = round((7.2 - ph_val) * (vol / 1000) * 100, 0) if ph_val and ph_val < 7.0 else 0
            # Chlor: Ziel 450mV | 1 Löffel hebt um ca. 50mV
            chlor_needed = round((450 - chlor_val) / 50, 2) if chlor_val and chlor_val < 450 else 0

            # 3. Kalender-Details
            cal_data = await self._get_next_calendar_event()
            next_event = cal_data.get("start")
            
            heat_up_time = self.calculate_heat_up_time(water_temp, 3000)
            preheat_start = next_event - timedelta(minutes=heat_up_time) if next_event else None
            
            # 4. Timer-Logik (Quick Chlorine / Pause)
            is_quick_chlorine = self.quick_chlorine_until and now < self.quick_chlorine_until
            is_paused = self.pause_until and now < self.pause_until

            # 5. Finale Steuerung
            should_main_on = (is_quick_chlorine or (not is_paused and (now >= (preheat_start or now + timedelta(days=1)) or self.is_bathing)))

            return {
                "water_temp": water_temp, "ph_val": ph_val, "chlor_val": chlor_val, "salt_val": salt_val,
                "ph_minus_g": ph_minus, "ph_plus_g": ph_plus, "chlor_spoons": chlor_needed,
                "next_event": next_event, "preheat_start": preheat_start,
                "heat_up_time_mins": heat_up_time, "is_paused": is_paused,
                "is_quick_chlorine": is_quick_chlorine, "should_main_on": should_main_on
            }
        except Exception as err:
            raise UpdateFailed(f"Update Error: {err}")

    async def _get_next_calendar_event(self):
        cal_id = self.entry.data.get(CONF_POOL_CALENDAR)
        if not cal_id: return {}
        now = dt_util.now()
        res = await self.hass.services.async_call("calendar", "get_events", 
            {"entity_id": cal_id, "start_date_time": now, "end_date_time": now + timedelta(days=7)}, 
            blocking=True, return_response=True)
        events = res.get(cal_id, {}).get("events", [])
        if not events: return {}
        first = events[0]
        return {"start": dt_util.parse_datetime(first["start"]), "summary": first.get("summary")}

    def calculate_heat_up_time(self, current_temp, power):
        if not current_temp or current_temp >= self.target_temp: return 0
        delta_t = self.target_temp - current_temp
        # Formel: $$t_{min} = \frac{V \cdot 1.16 \cdot \Delta T}{P} \cdot 60$$
        return round((self.entry.data.get(CONF_WATER_VOLUME, 1000) * 1.16 * delta_t) / power * 60)

    def _get_float_state(self, eid):
        s = self.hass.states.get(eid)
        return float(s.state) if s and s.state not in ("unknown", "unavailable") else None