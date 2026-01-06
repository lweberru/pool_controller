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
        self._last_should_main_on = None
        self._last_should_aux_on = None
        # Wiederherstellung von timers aus entry.options (falls vorhanden)
        self.pause_until = None
        self.quick_chlorine_until = None
        self.bathing_until = None
        if entry and entry.options:
            q = entry.options.get("quick_chlorine_until")
            if q:
                try:
                    self.quick_chlorine_until = dt_util.parse_datetime(q)
                except Exception:
                    self.quick_chlorine_until = None
            p = entry.options.get("pause_until")
            if p:
                try:
                    self.pause_until = dt_util.parse_datetime(p)
                except Exception:
                    self.pause_until = None
            b = entry.options.get("bathing_until")
            if b:
                try:
                    self.bathing_until = dt_util.parse_datetime(b)
                except Exception:
                    self.bathing_until = None
            f = entry.options.get(OPT_KEY_FILTER_UNTIL)
            if f:
                try:
                    self.filter_until = dt_util.parse_datetime(f)
                except Exception:
                    self.filter_until = None
            nf = entry.options.get(OPT_KEY_FILTER_NEXT)
            if nf:
                try:
                    self.next_filter_start = dt_util.parse_datetime(nf)
                except Exception:
                    self.next_filter_start = None
            # PV thresholds and filter config
            self.filter_minutes = int(entry.options.get(CONF_FILTER_DURATION, DEFAULT_FILTER_DURATION))
            self.filter_interval = int(entry.options.get(CONF_FILTER_INTERVAL, DEFAULT_FILTER_INTERVAL))
            self.pv_on_threshold = int(entry.options.get(CONF_PV_ON_THRESHOLD, DEFAULT_PV_ON))
            self.pv_off_threshold = int(entry.options.get(CONF_PV_OFF_THRESHOLD, DEFAULT_PV_OFF))
        else:
            self.filter_until = None
            self.next_filter_start = None
            self.filter_minutes = DEFAULT_FILTER_DURATION
            self.filter_interval = DEFAULT_FILTER_INTERVAL
            self.pv_on_threshold = DEFAULT_PV_ON
            self.pv_off_threshold = DEFAULT_PV_OFF

    async def activate_quick_chlorine(self, minutes: int = 5):
        """Aktiviere Stoßchlorung für `minutes` und persistiere den Timer in entry.options."""
        until = dt_util.now() + timedelta(minutes=minutes)
        self.quick_chlorine_until = until
        try:
            new_opts = {**self.entry.options, "quick_chlorine_until": until.isoformat()}
            await self.hass.config_entries.async_update_entry(self.entry, options=new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von quick_chlorine_until")
    async def deactivate_quick_chlorine(self):
        """Stoppe die Stoßchlorung und entferne den Timer."""
        self.quick_chlorine_until = None
        try:
            new_opts = {k: v for k, v in self.entry.options.items() if k != "quick_chlorine_until"}
            self.hass.config_entries.async_update_entry(self.entry, options=new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Löschen von quick_chlorine_until")
    async def activate_bathing(self, minutes: int = 60):
        """Start a bathing timer for `minutes` and persist in entry.options."""
        until = dt_util.now() + timedelta(minutes=minutes) if minutes > 0 else None
        self.bathing_until = until
        try:
            new_opts = {**self.entry.options, "bathing_until": until.isoformat() if until else None}
            self.hass.config_entries.async_update_entry(self.entry, options=new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von bathing_until")

    async def activate_filter(self, minutes: int = 30):
        """Start a filter cycle for `minutes`, persist filter_until and schedule next_filter_start."""
        now = dt_util.now()
        until = now + timedelta(minutes=minutes)
        next_start = now + timedelta(minutes=self.filter_interval)
        self.filter_until = until
        self.next_filter_start = next_start
        try:
            new_opts = {**self.entry.options, OPT_KEY_FILTER_UNTIL: until.isoformat(), OPT_KEY_FILTER_NEXT: next_start.isoformat()}
            self.hass.config_entries.async_update_entry(self.entry, options=new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von filter timers")

    async def deactivate_filter(self):
        """Stop current filter and schedule next start if needed."""
        self.filter_until = None
        try:
            # set next_filter_start to now + interval
            next_start = dt_util.now() + timedelta(minutes=self.filter_interval)
            new_opts = {**self.entry.options}
            new_opts.pop(OPT_KEY_FILTER_UNTIL, None)
            new_opts[OPT_KEY_FILTER_NEXT] = next_start.isoformat()
            self.next_filter_start = next_start
            self.hass.config_entries.async_update_entry(self.entry, options=new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Deaktivieren von filter timers")

    async def deactivate_bathing(self):
        """Clear the bathing timer and persist change."""
        self.bathing_until = None
        try:
            new_opts = {k: v for k, v in self.entry.options.items() if k != "bathing_until"}
            self.hass.config_entries.async_update_entry(self.entry, options=new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Löschen von bathing_until")

    async def activate_pause(self, minutes: int = 30):
        """Setze Pause für `minutes` und persistiere den Timer in entry.options."""
        until = dt_util.now() + timedelta(minutes=minutes) if minutes > 0 else None
        self.pause_until = until
        try:
            new_opts = {**self.entry.options, "pause_until": until.isoformat() if until else None}
            self.hass.config_entries.async_update_entry(self.entry, options=new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von pause_until")

    async def _async_update_data(self):
        try:
            now = dt_util.now()
            conf = {**self.entry.data, **self.entry.options}
            
            # Sensoren
            water_temp = self._get_float(conf.get(CONF_TEMP_WATER))
            outdoor_temp = self._get_float(conf.get(CONF_TEMP_OUTDOOR))
            ph_val = self._get_float(conf.get(CONF_PH_SENSOR))
            chlor_val = self._get_float(conf.get(CONF_CHLORINE_SENSOR))
            main_power = self._get_float(conf.get(CONF_MAIN_POWER_SENSOR))
            aux_power = self._get_float(conf.get(CONF_AUX_POWER_SENSOR))
            
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
            # Heizung-Leistung: falls ein Power-Sensor konfiguriert ist, verwenden, sonst Fallback 3000W
            power_w = int(main_power) if main_power and main_power > 0 else 3000

            # Volumen (Liter) und Temperaturdifferenz (DeltaT).
            vol_l = conf.get(CONF_WATER_VOLUME, DEFAULT_VOL)
            # Wenn Wassertemperatur fehlt, konservativer Default 20°C (statt Fehler)
            measured_temp = water_temp if water_temp is not None else 20.0
            delta_t = max(0.0, self.target_temp - measured_temp)

            heat_time = None
            if vol_l is not None and power_w > 0 and delta_t > 0:
                # t_min in Minuten: V * 1.16 * deltaT / P * 60
                t_min = (vol_l * 1.16 * delta_t) / float(power_w) * 60.0
                try:
                    heat_time = max(0, int(round(t_min)))
                except Exception:
                    heat_time = None

            cal_data = await self._get_next_event(conf.get(CONF_POOL_CALENDAR))

            next_start_mins = None
            if cal_data.get("start") and heat_time is not None:
                preheat_time = cal_data["start"] - timedelta(minutes=heat_time)
                next_start_mins = max(0, round((preheat_time - now).total_seconds() / 60))
            bathing_active = self.bathing_until is not None and now < self.bathing_until
            filter_active = getattr(self, "filter_until", None) is not None and now < getattr(self, "filter_until", None)
            
            # Initialisiere next_filter_start wenn nicht gesetzt (z.B. nach Neustart)
            if not getattr(self, "next_filter_start", None):
                self.next_filter_start = now + timedelta(minutes=self.filter_interval)
            
            next_filter_mins = None
            if getattr(self, "next_filter_start", None):
                next_filter_mins = max(0, round((self.next_filter_start - now).total_seconds() / 60))
            # PV sensor logic
            pv_val = self._get_float(conf.get(CONF_PV_SURPLUS_SENSOR))
            pv_allows = False
            if pv_val is not None:
                if pv_val >= getattr(self, "pv_on_threshold", DEFAULT_PV_ON):
                    pv_allows = True
                elif pv_val <= getattr(self, "pv_off_threshold", DEFAULT_PV_OFF):
                    pv_allows = False
            # quiet time check: C and E should not activate during quiet; A/B/D always allowed
            def _in_quiet_period(cfg):
                try:
                    now_local = dt_util.now()
                    t = now_local.time()
                    weekday = now_local.weekday()
                    if weekday >= 5:
                        start_s = cfg.get(CONF_QUIET_START_WEEKEND, DEFAULT_Q_START_WE)
                        end_s = cfg.get(CONF_QUIET_END_WEEKEND, DEFAULT_Q_END_WE)
                    else:
                        start_s = cfg.get(CONF_QUIET_START, DEFAULT_Q_START)
                        end_s = cfg.get(CONF_QUIET_END, DEFAULT_Q_END)
                    fmt = lambda s: dt_util.parse_time(s)
                    start_t = fmt(start_s)
                    end_t = fmt(end_s)
                    if start_t <= end_t:
                        return start_t <= t <= end_t
                    # overnight (e.g., 22:00 - 08:00)
                    return t >= start_t or t <= end_t
                except Exception:
                    return False

            in_quiet = _in_quiet_period(conf)

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
                "next_event_end": cal_data.get("end"),
                "next_event_summary": cal_data.get("summary"),
                "next_start_mins": next_start_mins,
                "is_paused": self.pause_until is not None and now < self.pause_until,
                "pause_until": self.pause_until,
                "is_quick_chlor": self.quick_chlorine_until is not None and now < self.quick_chlorine_until,
                # Priorisiere Stoßchlorung: wenn active, Main sollte an sein (5 Minuten Button-Press)
                "is_bathing": bathing_active,
                "bathing_until": self.bathing_until,
                "filter_active": filter_active,
                "filter_until": getattr(self, "filter_until", None),
                "next_filter_mins": next_filter_mins,
                # Aux-Heizung einschalten, wenn Temperatur signifikant unter Ziel liegt
                "should_aux_on": (delta_t > 1.0),
                "pv_allows": pv_allows,
                "in_quiet": in_quiet,
                "main_power": round(main_power, 1) if main_power is not None else None,
                "aux_power": round(aux_power, 1) if aux_power is not None else None,
                "should_main_on": (
                    (self.quick_chlorine_until is not None and now < self.quick_chlorine_until)
                    or frost_danger
                    or bathing_active
                    or (filter_active and not in_quiet)
                    or (next_start_mins is not None and next_start_mins == 0)
                    or (pv_allows and not in_quiet)
                )
            }

            # After computing desired states, ensure physical switches follow the desired state
            try:
                main_switch_id = conf.get(CONF_MAIN_SWITCH)
                aux_switch_id = conf.get(CONF_AUX_HEATING_SWITCH)
                demo = conf.get(CONF_DEMO_MODE, False)

                desired_main = data.get("should_main_on")
                desired_aux = data.get("should_aux_on")

                # Start calendar-driven bathing: if event is ongoing, ensure bathing timer active
                if cal_data.get("start") and cal_data.get("end"):
                    if now >= cal_data["start"] and now < cal_data["end"]:
                        # start bathing for remaining event duration if not already active
                        remaining_min = max(1, int((cal_data["end"] - now).total_seconds() / 60))
                        if not bathing_active:
                            await self.activate_bathing(minutes=remaining_min)

                # Auto-start filter when next_filter_start reached
                if getattr(self, "next_filter_start", None) and now >= self.next_filter_start and not filter_active:
                    # only start if not in quiet and PV allows (or PV not configured)
                    if (not in_quiet) and (pv_allows or conf.get(CONF_PV_SURPLUS_SENSOR) is None):
                        await self.activate_filter(minutes=self.filter_minutes)

                # Toggle main switch according to desired state
                if desired_main != self._last_should_main_on:
                    if desired_main:
                        if not demo and main_switch_id:
                            await self.hass.services.async_call("switch", "turn_on", {"entity_id": main_switch_id})
                    else:
                        # don't turn off main while bathing
                        if not bathing_active and not demo and main_switch_id:
                            await self.hass.services.async_call("switch", "turn_off", {"entity_id": main_switch_id})
                    self._last_should_main_on = desired_main

                # Toggle aux switch according to desired_aux
                if desired_aux != self._last_should_aux_on:
                    if desired_aux:
                        if not demo and aux_switch_id:
                            await self.hass.services.async_call("switch", "turn_on", {"entity_id": aux_switch_id})
                    else:
                        if not demo and aux_switch_id:
                            await self.hass.services.async_call("switch", "turn_off", {"entity_id": aux_switch_id})
                    self._last_should_aux_on = desired_aux
            except Exception:
                _LOGGER.exception("Fehler beim Anwenden der gewünschten Schaltzustände")
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
            if not events:
                return {}
            ev = events[0]
            start = dt_util.parse_datetime(ev.get("start")) if ev.get("start") else None
            end = dt_util.parse_datetime(ev.get("end")) if ev.get("end") else None
            summary = ev.get("summary", "")
            return {k: v for k, v in (("start", start), ("end", end), ("summary", summary)) if v}
        except: return {}