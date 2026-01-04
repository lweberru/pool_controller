import logging
from datetime import timedelta, datetime
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .const import *

_LOGGER = logging.getLogger(__name__)

class PoolControllerDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.entry = entry
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=30))
        self.target_temp = 38.0
        self.is_bathing = False
        self.pause_until = None
        self.quick_chlorine_until = None

    async def _async_update_data(self):
        try:
            now = dt_util.now()
            conf = {**self.entry.data, **self.entry.options}
            
            # Sensoren
            water_temp = self._get_float(conf.get(CONF_TEMP_WATER))
            outdoor_temp = self._get_float(conf.get(CONF_TEMP_OUTDOOR))
            ph_val = self._get_float(conf.get(CONF_PH_SENSOR))
            chlor_val = self._get_float(conf.get(CONF_CHLORINE_SENSOR))
            
            # 1. Frost & Wochenende
            frost_danger = outdoor_temp is not None and outdoor_temp < 3.0
            is_holiday = await self._check_holiday(conf.get(CONF_HOLIDAY_CALENDAR))
            we_or_holiday = is_holiday or (now.weekday() >= 5)

            # 2. Chemie (Ziel pH 7.2)
            vol_f = conf.get(CONF_WATER_VOLUME, DEFAULT_VOL) / 1000
            ph_minus = max(0, round((ph_val - 7.3) * 100 * vol_f)) if ph_val and ph_val > 7.3 else 0
            ph_plus = max(0, round((7.1 - ph_val) * 100 * vol_f)) if ph_val and ph_val < 7.1 else 0
            chlor_spoons = max(0, round((650 - chlor_val) / 50, 1)) if chlor_val and chlor_val < 650 else 0

            # 3. Kalender & Aufheizzeit
            heat_time = round((conf.get(CONF_WATER_VOLUME, 1000) * 1.16 * (self.target_temp - (water_temp or 20))) / 3000 * 60)
            cal_data = await self._get_next_event(conf.get(CONF_POOL_CALENDAR))
            
            next_start_mins = None
            if cal_data.get("start"):
                preheat_time = cal_data["start"] - timedelta(minutes=heat_time)
                next_start_mins = max(0, round((preheat_time - now).total_seconds() / 60))

            return {
                "water_temp": round(water_temp, 1) if water_temp else None,
                "ph_val": round(ph_val, 2) if ph_val else None,
                "chlor_val": int(chlor_val) if chlor_val else None,
                "ph_minus_g": ph_minus,
                "ph_plus_g": ph_plus,
                "chlor_spoons": chlor_spoons,
                "is_we_holiday": we_or_holiday,
                "frost_danger": frost_danger,
                "next_event": cal_data.get("start"),
                "next_start_mins": next_start_mins,
                "is_paused": self.pause_until is not None and now < self.pause_until,
                "is_quick_chlor": self.quick_chlorine_until is not None and now < self.quick_chlorine_until,
                "should_main_on": (frost_danger or self.is_bathing or (next_start_mins is not None and next_start_mins == 0))
            }
        except Exception as err:
            _LOGGER.error("Update Error: %s", err)
            raise UpdateFailed(err)

    def _get_float(self, eid):
        if not eid: return None
        state = self.hass.states.get(eid)
        try: return float(state.state) if state and state.state not in ("unknown", "unavailable") else None
        except: return None

    async def _check_holiday(self, cal_id):
        if not cal_id: return False
        try:
            res = await self.hass.services.async_call("calendar", "get_events", {"entity_id": cal_id, "start_date_time": dt_util.now().replace(hour=0, minute=0), "end_date_time": dt_util.now().replace(hour=23, minute=59)}, blocking=True, return_response=True)
            return len(res.get(cal_id, {}).get("events", [])) > 0
        except: return False

    async def _get_next_event(self, cal_id):
        if not cal_id: return {}
        try:
            res = await self.hass.services.async_call("calendar", "get_events", {"entity_id": cal_id, "start_date_time": dt_util.now(), "end_date_time": dt_util.now() + timedelta(days=7)}, blocking=True, return_response=True)
            events = res.get(cal_id, {}).get("events", [])
            return {"start": dt_util.parse_datetime(events[0]["start"])} if events else {}
        except: return {}