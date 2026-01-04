import logging
from datetime import timedelta, datetime
import asyncio

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.components.calendar import async_get_events

from .const import *

_LOGGER = logging.getLogger(__name__)

class PoolControllerDataCoordinator(DataUpdateCoordinator):
    """Zentrale Logik für den Whirlpool-Controller."""

    def __init__(self, hass: HomeAssistant, entry):
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        
        self.target_temp = 38.0
        self.is_bathing = False
        self.last_filter_run = dt_util.now() - timedelta(hours=12)
        self.demo_mode = entry.data.get(CONF_DEMO_MODE, False)
        
        # Pausen-Logik
        self.pause_until = None

    async def _async_update_data(self):
        try:
            now = dt_util.now()
            
            # 1. Daten abrufen
            water_temp = self._get_float_state(self.entry.data.get(CONF_TEMP_WATER))
            outdoor_temp = self._get_float_state(self.entry.data.get(CONF_TEMP_OUTDOOR))
            pv_surplus = self._get_float_state(self.entry.data.get(CONF_PV_SURPLUS_SENSOR))
            conductivity = self._get_float_state(self.entry.data.get(CONF_TDS_SENSOR))
            
            # Dynamische Leistungsermittlung
            main_power = self._get_float_state(self.entry.data.get(CONF_MAIN_POWER_SENSOR)) or DEFAULT_MAIN_POWER
            aux_power = self._get_float_state(self.entry.data.get(CONF_AUX_POWER_SENSOR)) or DEFAULT_AUX_POWER
            
            # 2. Berechnungen
            tds_value = self.calculate_tds(conductivity)
            is_holiday = await self._is_holiday()
            is_quiet = self._check_quiet_time(is_holiday)
            
            # Pausen-Status prüfen
            is_paused = self.pause_until is not None and now < self.pause_until
            if is_paused and now >= self.pause_until:
                self.pause_until = None
                is_paused = False

            # 3. Thermik
            total_heating_power = main_power + aux_power
            heat_up_time = self.calculate_heat_up_time(water_temp, total_heating_power)
            frost_danger = outdoor_temp is not None and outdoor_temp < 3.0
            
            # 4. Kalender & Filter
            preheat_needed = await self._check_calendar_preheat(heat_up_time)
            filter_needed = self._check_filter_requirement()

            # 5. Entscheidungs-Logik
            # Frostschutz gewinnt IMMER, auch vor der Pause
            should_main_on = (
                frost_danger or 
                (not is_paused and (preheat_needed or self.is_bathing or filter_needed or 
                (pv_surplus is not None and pv_surplus > total_heating_power and water_temp < self.target_temp)))
            )

            # Ruhezeit-Override (außer Frostschutz)
            if is_quiet and not frost_danger:
                should_main_on = False

            should_aux_on = should_main_on and water_temp is not None and (self.target_temp - water_temp > 2.0)
            
            # Keine Zusatzheizung beim reinen Filtern
            if filter_needed and not preheat_needed and not self.is_bathing:
                should_aux_on = False

            return {
                "water_temp": water_temp,
                "outdoor_temp": outdoor_temp,
                "tds_value": tds_value,
                "heat_up_time_mins": heat_up_time,
                "frost_danger": frost_danger,
                "is_quiet_time": is_quiet,
                "is_paused": is_paused,
                "should_main_on": should_main_on,
                "should_aux_on": should_aux_on,
                "demo_mode": self.demo_mode,
                "is_holiday": is_holiday
            }

        except Exception as err:
            raise UpdateFailed(f"Update fehlgeschlagen: {err}")

    def calculate_tds(self, conductivity):
        """Berechnet TDS aus Leitfähigkeit (ppm = µS/cm * 0.64)."""
        if conductivity is None: return None
        return round(conductivity * 0.64)

    async def set_pause(self, minutes=30):
        """Setzt den Pool für X Minuten auf Pause."""
        self.pause_until = dt_util.now() + timedelta(minutes=minutes)
        await self.async_request_refresh()

    def _get_float_state(self, entity_id):
        if not entity_id: return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"): return None
        try: return float(state.state)
        except ValueError: return None

    async def _is_holiday(self):
        holiday_cal = self.entry.data.get(CONF_HOLIDAY_CALENDAR)
        if not holiday_cal: return False
        now = dt_util.now()
        events = await async_get_events(self.hass, holiday_cal, dt_util.start_of_local_day(now), dt_util.end_of_local_day(now))
        return len(events) > 0

    def _check_quiet_time(self, is_holiday):
        now_time = dt_util.now().time()
        start = datetime.strptime(self.entry.data.get(CONF_QUIET_START, "22:00"), "%H:%M").time()
        end = datetime.strptime(self.entry.data.get(CONF_QUIET_END, "06:00"), "%H:%M").time()
        if start <= end: return start <= now_time <= end
        return now_time >= start or now_time <= end

    def calculate_heat_up_time(self, current_temp, power_watt):
        if current_temp is None or current_temp >= self.target_temp or power_watt <= 0: return 0
        volume = self.entry.data.get(CONF_WATER_VOLUME, 1000)
        delta_t = self.target_temp - current_temp
        hours = (volume * 1.16 * delta_t) / power_watt
        return round(hours * 60)

    async def _check_calendar_preheat(self, heat_up_mins):
        cal_id = self.entry.data.get(CONF_POOL_CALENDAR)
        if not cal_id or heat_up_mins <= 0: return False
        now = dt_util.now()
        events = await async_get_events(self.hass, cal_id, now, now + timedelta(hours=24))
        for event in events:
            if (event.start - timedelta(minutes=heat_up_mins)) <= now <= event.start:
                return True
        return False

    def _check_filter_requirement(self):
        return (dt_util.now() - self.last_filter_run) > timedelta(hours=12)