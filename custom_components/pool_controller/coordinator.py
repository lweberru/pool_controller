import logging
import re
import inspect
from datetime import timedelta, datetime
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.helpers import entity_registry as er
from .const import *

_LOGGER = logging.getLogger(__name__)

class PoolControllerDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.entry = entry
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=30))
        # Target temperature: prefer persisted option, else config value, else default.
        self.target_temp = DEFAULT_TARGET_TEMP
        if entry:
            try:
                merged = {**(entry.data or {}), **(entry.options or {})}
                if merged.get(OPT_KEY_TARGET_TEMP) is not None:
                    self.target_temp = float(merged.get(OPT_KEY_TARGET_TEMP))
                elif merged.get(CONF_TARGET_TEMP) is not None:
                    self.target_temp = float(merged.get(CONF_TARGET_TEMP))
            except Exception:
                self.target_temp = DEFAULT_TARGET_TEMP
        self._last_should_main_on = None
        self._last_should_pump_on = None
        self._last_should_aux_on = None
        # Track last toggle attempts per entity to avoid rapid retry loops
        # when an entity becomes unavailable after a toggle (prevents oscillation).
        self._last_toggle_attempts = {}
        # Master-Enable für Zusatzheizung: vom gemergten config/options lesen (default: False)
        try:
            merged = {**(entry.data or {}), **(entry.options or {})} if entry else {}
            self.aux_enabled = bool(merged.get(CONF_ENABLE_AUX_HEATING, False))
        except Exception:
            self.aux_enabled = False
        # Toggle debounce seconds (configurable via entry.options or defaults)
        try:
            merged_td = {**(entry.data or {}), **(entry.options or {})} if entry else {}
            self.toggle_debounce_seconds = int(merged_td.get(CONF_TOGGLE_DEBOUNCE_SECONDS, DEFAULT_TOGGLE_DEBOUNCE_SECONDS))
        except Exception:
            self.toggle_debounce_seconds = DEFAULT_TOGGLE_DEBOUNCE_SECONDS
        self.maintenance_active = False
        # HVAC enabled state (thermostat-style heating when PV optimization is disabled).
        self.hvac_enabled = True
        # Internal demand states (hysteresis)
        self._aux_heat_demand = False
        self._pv_heat_demand = False
        # PV smoothing / stability internal state
        self._pv_smoothed = None
        self._pv_allows_effective = False
        self._pv_candidate_since = None
        self._pv_last_start = None
        # Wiederherstellung von Timern aus entry.options (falls vorhanden)
        self.manual_timer_until = None
        self.manual_timer_type = None
        self.manual_timer_duration = None

        self.auto_filter_until = None
        self.auto_filter_duration = None

        self.pause_until = None
        self.pause_duration = None

        # Frost-Timer (analog zu manual/auto_filter/pause)
        self.frost_timer_until = None
        self.frost_timer_duration = None

        self._did_migrate_timers = False
        if entry and entry.options:
            self.maintenance_active = bool(entry.options.get(OPT_KEY_MAINTENANCE_ACTIVE, False))
            self.hvac_enabled = bool(entry.options.get(OPT_KEY_HVAC_ENABLED, True))
            # New timers
            mu = entry.options.get(OPT_KEY_MANUAL_UNTIL)
            if mu:
                try:
                    self.manual_timer_until = dt_util.parse_datetime(mu)
                except Exception:
                    self.manual_timer_until = None
            self.manual_timer_type = entry.options.get(OPT_KEY_MANUAL_TYPE) or None
            try:
                self.manual_timer_duration = int(entry.options.get(OPT_KEY_MANUAL_DURATION)) if entry.options.get(OPT_KEY_MANUAL_DURATION) is not None else None
            except Exception:
                self.manual_timer_duration = None

            au = entry.options.get(OPT_KEY_AUTO_FILTER_UNTIL)
            if au:
                try:
                    self.auto_filter_until = dt_util.parse_datetime(au)
                except Exception:
                    self.auto_filter_until = None
            try:
                self.auto_filter_duration = int(entry.options.get(OPT_KEY_AUTO_FILTER_DURATION)) if entry.options.get(OPT_KEY_AUTO_FILTER_DURATION) is not None else None
            except Exception:
                self.auto_filter_duration = None

            pu = entry.options.get(OPT_KEY_PAUSE_UNTIL)
            if pu:
                try:
                    self.pause_until = dt_util.parse_datetime(pu)
                except Exception:
                    self.pause_until = None
            try:
                self.pause_duration = int(entry.options.get(OPT_KEY_PAUSE_DURATION)) if entry.options.get(OPT_KEY_PAUSE_DURATION) is not None else None
            except Exception:
                self.pause_duration = None

            nf = entry.options.get(OPT_KEY_FILTER_NEXT)
            if nf:
                try:
                    self.next_filter_start = dt_util.parse_datetime(nf)
                except Exception:
                    self.next_filter_start = None
            # PV thresholds and filter config
            self.filter_minutes = int(entry.options.get(CONF_FILTER_DURATION, entry.data.get(CONF_FILTER_DURATION, DEFAULT_FILTER_DURATION)))
            self.filter_interval = int(entry.options.get(CONF_FILTER_INTERVAL, entry.data.get(CONF_FILTER_INTERVAL, DEFAULT_FILTER_INTERVAL)))
            # Filterlauf darf nie länger als das Intervall sein
            if self.filter_minutes > self.filter_interval:
                self.filter_minutes = self.filter_interval
            self.chlorine_duration = int(entry.options.get(CONF_CHLORINE_DURATION, entry.data.get(CONF_CHLORINE_DURATION, DEFAULT_CHLORINE_DURATION)))
            self.pv_on_threshold = int(entry.options.get(CONF_PV_ON_THRESHOLD, entry.data.get(CONF_PV_ON_THRESHOLD, DEFAULT_PV_ON)))
            self.pv_off_threshold = int(entry.options.get(CONF_PV_OFF_THRESHOLD, entry.data.get(CONF_PV_OFF_THRESHOLD, DEFAULT_PV_OFF)))
            # PV smoothing / stability defaults from options or data
            try:
                self.pv_smooth_window = int(entry.options.get(CONF_PV_SMOOTH_WINDOW_SECONDS, entry.data.get(CONF_PV_SMOOTH_WINDOW_SECONDS, DEFAULT_PV_SMOOTH_WINDOW_SECONDS)))
            except Exception:
                self.pv_smooth_window = DEFAULT_PV_SMOOTH_WINDOW_SECONDS
            try:
                self.pv_stability_seconds = int(entry.options.get(CONF_PV_STABILITY_SECONDS, entry.data.get(CONF_PV_STABILITY_SECONDS, DEFAULT_PV_STABILITY_SECONDS)))
            except Exception:
                self.pv_stability_seconds = DEFAULT_PV_STABILITY_SECONDS
            try:
                self.pv_min_run_minutes = int(entry.options.get(CONF_PV_MIN_RUN_MINUTES, entry.data.get(CONF_PV_MIN_RUN_MINUTES, DEFAULT_PV_MIN_RUN_MINUTES)))
            except Exception:
                self.pv_min_run_minutes = DEFAULT_PV_MIN_RUN_MINUTES
        else:
            self.manual_timer_until = None
            self.manual_timer_type = None
            self.manual_timer_duration = None

            self.auto_filter_until = None
            self.auto_filter_duration = None

            self.pause_until = None
            self.pause_duration = None

            self.frost_timer_until = None
            self.frost_timer_duration = None

            self.next_filter_start = None
            self.filter_minutes = DEFAULT_FILTER_DURATION
            self.filter_interval = DEFAULT_FILTER_INTERVAL
            self.pv_on_threshold = DEFAULT_PV_ON
            self.pv_off_threshold = DEFAULT_PV_OFF
            self.pv_smooth_window = DEFAULT_PV_SMOOTH_WINDOW_SECONDS
            self.pv_stability_seconds = DEFAULT_PV_STABILITY_SECONDS
            self.pv_min_run_minutes = DEFAULT_PV_MIN_RUN_MINUTES
            self.hvac_enabled = True

    def _estimate_minutes_to_target(self, conf: dict, water_temp: float | None) -> int | None:
        """Best-effort estimate how long heating to target may take (in minutes)."""
        try:
            vol_l = conf.get(CONF_WATER_VOLUME, DEFAULT_VOL)
            vol_l = float(vol_l) if vol_l is not None else None
        except Exception:
            vol_l = None

        try:
            target_temp = float(getattr(self, "target_temp", DEFAULT_TARGET_TEMP))
        except Exception:
            target_temp = DEFAULT_TARGET_TEMP

        measured_temp = water_temp if water_temp is not None else 20.0
        try:
            delta_t = max(0.0, float(target_temp) - float(measured_temp))
        except Exception:
            delta_t = 0.0
        if delta_t <= 0:
            return 0

        # Heating power model (same intent as in _async_update_data): base + (aux if enabled)
        try:
            base_w = int(conf.get(CONF_HEATER_BASE_POWER_W, DEFAULT_HEATER_BASE_POWER_W))
        except Exception:
            base_w = DEFAULT_HEATER_BASE_POWER_W
        try:
            aux_w = int(conf.get(CONF_HEATER_AUX_POWER_W, DEFAULT_HEATER_AUX_POWER_W))
        except Exception:
            aux_w = DEFAULT_HEATER_AUX_POWER_W
        base_w = max(0, int(base_w or 0))
        aux_w = max(0, int(aux_w or 0))

        try:
            legacy_present = CONF_HEATER_POWER_W in conf and conf.get(CONF_HEATER_POWER_W) is not None
            split_effective_raw = base_w + aux_w
            if legacy_present and split_effective_raw <= 0:
                base_w = max(0, int(float(conf.get(CONF_HEATER_POWER_W))))
        except Exception:
            pass

        enable_aux = bool(conf.get(CONF_ENABLE_AUX_HEATING, False))
        power_w = base_w + (aux_w if enable_aux else 0)
        if not power_w or power_w <= 0:
            try:
                power_w = int(conf.get(CONF_HEATER_POWER_W, DEFAULT_HEATER_POWER_W))
            except Exception:
                power_w = DEFAULT_HEATER_POWER_W
        if not power_w or power_w <= 0:
            power_w = DEFAULT_HEATER_POWER_W

        if not vol_l or vol_l <= 0 or power_w <= 0:
            return None

        # t_min in Minuten: V * 1.16 * deltaT / P * 60
        t_min = (vol_l * 1.16 * delta_t) / float(power_w) * 60.0
        try:
            return max(0, int(round(t_min)))
        except Exception:
            return None

    async def async_migrate_legacy_timers(self):
        """Best-effort Migration: alte Timer-Optionen auf neue Keys umlegen und alte Keys entfernen."""
        if self._did_migrate_timers or not self.entry or not self.entry.options:
            return

        now = dt_util.now()
        opts = dict(self.entry.options)
        changed = False

        def _parse_dt(val):
            if not val:
                return None
            try:
                return dt_util.parse_datetime(val)
            except Exception:
                return None

        # Legacy keys
        legacy_pause_until = _parse_dt(opts.get("pause_until"))
        legacy_bathing_until = _parse_dt(opts.get("bathing_until"))
        legacy_quick_chlor_until = _parse_dt(opts.get("quick_chlorine_until"))
        legacy_filter_until = _parse_dt(opts.get("filter_until"))

        # Pause migration (keep pause_until key, add duration)
        if legacy_pause_until and legacy_pause_until > now and self.pause_until is None:
            self.pause_until = legacy_pause_until
            self.pause_duration = max(1, int((legacy_pause_until - now).total_seconds() / 60))
            opts[OPT_KEY_PAUSE_UNTIL] = legacy_pause_until.isoformat()
            opts[OPT_KEY_PAUSE_DURATION] = self.pause_duration
            changed = True

        # Manual timer migration preference order: bathing > chlorine
        if self.manual_timer_until is None:
            if legacy_bathing_until and legacy_bathing_until > now:
                self.manual_timer_until = legacy_bathing_until
                self.manual_timer_type = "bathing"
                self.manual_timer_duration = max(1, int((legacy_bathing_until - now).total_seconds() / 60))
                opts[OPT_KEY_MANUAL_UNTIL] = legacy_bathing_until.isoformat()
                opts[OPT_KEY_MANUAL_TYPE] = self.manual_timer_type
                opts[OPT_KEY_MANUAL_DURATION] = self.manual_timer_duration
                changed = True
            elif legacy_quick_chlor_until and legacy_quick_chlor_until > now:
                self.manual_timer_until = legacy_quick_chlor_until
                self.manual_timer_type = "chlorine"
                self.manual_timer_duration = max(1, int((legacy_quick_chlor_until - now).total_seconds() / 60))
                opts[OPT_KEY_MANUAL_UNTIL] = legacy_quick_chlor_until.isoformat()
                opts[OPT_KEY_MANUAL_TYPE] = self.manual_timer_type
                opts[OPT_KEY_MANUAL_DURATION] = self.manual_timer_duration
                changed = True

        # Auto filter migration
        if self.auto_filter_until is None and legacy_filter_until and legacy_filter_until > now:
            self.auto_filter_until = legacy_filter_until
            self.auto_filter_duration = max(1, int((legacy_filter_until - now).total_seconds() / 60))
            opts[OPT_KEY_AUTO_FILTER_UNTIL] = legacy_filter_until.isoformat()
            opts[OPT_KEY_AUTO_FILTER_DURATION] = self.auto_filter_duration
            changed = True

        # Remove legacy keys
        for k in ("bathing_until", "quick_chlorine_until", "filter_until"):
            if k in opts:
                opts.pop(k, None)
                changed = True

        if changed:
            try:
                await self._async_update_entry_options(opts)
            except Exception:
                _LOGGER.exception("Fehler beim Migrieren alter Timer-Optionen")

        self._did_migrate_timers = True

    async def activate_manual_timer(self, timer_type: str, minutes: int):
        """Start/überschreibe den gemeinsamen Manual-Timer."""
        timer_type = (timer_type or "").strip().lower()
        if timer_type not in ("bathing", "chlorine", "filter"):
            raise ValueError("invalid manual timer_type")
        minutes = int(minutes)
        if minutes <= 0:
            await self.deactivate_manual_timer()
            return
        now = dt_util.now()
        until = now + timedelta(minutes=minutes)
        self.manual_timer_until = until
        self.manual_timer_type = timer_type
        self.manual_timer_duration = minutes

        # reschedule next auto filter start when manual filter started
        new_opts = {**self.entry.options}
        new_opts[OPT_KEY_MANUAL_UNTIL] = until.isoformat()
        new_opts[OPT_KEY_MANUAL_TYPE] = timer_type
        new_opts[OPT_KEY_MANUAL_DURATION] = minutes
        if timer_type == "filter":
            next_start = now + timedelta(minutes=self.filter_interval)
            self.next_filter_start = next_start
            new_opts[OPT_KEY_FILTER_NEXT] = next_start.isoformat()
        try:
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von manual timer")

    async def deactivate_manual_timer(self, only_type: str | None = None):
        """Stoppt den Manual-Timer; optional nur wenn Typ passt."""
        if only_type and self.manual_timer_type != only_type:
            return
        self.manual_timer_until = None
        self.manual_timer_type = None
        self.manual_timer_duration = None
        try:
            new_opts = {**self.entry.options}
            new_opts.pop(OPT_KEY_MANUAL_UNTIL, None)
            new_opts.pop(OPT_KEY_MANUAL_TYPE, None)
            new_opts.pop(OPT_KEY_MANUAL_DURATION, None)
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Löschen von manual timer")

    async def activate_pause(self, minutes: int = 60):
        """Setze Pause für `minutes` und persistiere den Timer."""
        minutes = int(minutes)
        if minutes <= 0:
            await self.deactivate_pause()
            return
        until = dt_util.now() + timedelta(minutes=minutes)
        self.pause_until = until
        self.pause_duration = minutes
        try:
            new_opts = {**self.entry.options, OPT_KEY_PAUSE_UNTIL: until.isoformat(), OPT_KEY_PAUSE_DURATION: minutes}
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von pause timer")

    async def deactivate_pause(self):
        self.pause_until = None
        self.pause_duration = None
        try:
            new_opts = {**self.entry.options}
            new_opts.pop(OPT_KEY_PAUSE_UNTIL, None)
            new_opts.pop(OPT_KEY_PAUSE_DURATION, None)
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Löschen von pause timer")

    async def _start_auto_filter(self, minutes: int | None = None):
        """Startet den Auto-Filterzyklus (intervallbasiert) und persistiert bis + nächste Startzeit."""
        now = dt_util.now()
        run_minutes = int(minutes if minutes is not None else self.filter_minutes)
        if run_minutes <= 0:
            return
        until = now + timedelta(minutes=run_minutes)
        next_start = now + timedelta(minutes=self.filter_interval)
        self.auto_filter_until = until
        self.auto_filter_duration = run_minutes
        self.next_filter_start = next_start
        try:
            new_opts = {**self.entry.options}
            new_opts[OPT_KEY_AUTO_FILTER_UNTIL] = until.isoformat()
            new_opts[OPT_KEY_AUTO_FILTER_DURATION] = run_minutes
            new_opts[OPT_KEY_FILTER_NEXT] = next_start.isoformat()
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von auto filter timer")

    async def stop_filter(self):
        """Stoppt laufende Filter-Aktivität (Manual-Typ filter und Auto-Filter-Timer)."""
        now = dt_util.now()
        if self.manual_timer_type == "filter":
            await self.deactivate_manual_timer(only_type="filter")

        self.auto_filter_until = None
        self.auto_filter_duration = None
        try:
            next_start = now + timedelta(minutes=self.filter_interval)
            self.next_filter_start = next_start
            new_opts = {**self.entry.options}
            new_opts.pop(OPT_KEY_AUTO_FILTER_UNTIL, None)
            new_opts.pop(OPT_KEY_AUTO_FILTER_DURATION, None)
            new_opts[OPT_KEY_FILTER_NEXT] = next_start.isoformat()
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Stoppen von filter")

    async def set_maintenance(self, active: bool):
        """Aktiviert/deaktiviert Wartung (Hard-Lockout) und persistiert den Zustand."""
        active = bool(active)
        if active == bool(getattr(self, "maintenance_active", False)):
            return

        self.maintenance_active = active
        try:
            new_opts = {**self.entry.options}
            if active:
                new_opts[OPT_KEY_MAINTENANCE_ACTIVE] = True
                # Maintenance is a hard lockout: disable HVAC + clear timers so we don't auto-resume.
                self.hvac_enabled = False
                new_opts[OPT_KEY_HVAC_ENABLED] = False

                # Clear any running timers (manual, pause, auto-filter) best effort.
                self.manual_timer_until = None
                self.manual_timer_type = None
                self.manual_timer_duration = None
                self.auto_filter_until = None
                self.auto_filter_duration = None
                self.pause_until = None
                self.pause_duration = None

                new_opts.pop(OPT_KEY_MANUAL_UNTIL, None)
                new_opts.pop(OPT_KEY_MANUAL_TYPE, None)
                new_opts.pop(OPT_KEY_MANUAL_DURATION, None)
                new_opts.pop(OPT_KEY_AUTO_FILTER_UNTIL, None)
                new_opts.pop(OPT_KEY_AUTO_FILTER_DURATION, None)
                new_opts.pop(OPT_KEY_PAUSE_UNTIL, None)
                new_opts.pop(OPT_KEY_PAUSE_DURATION, None)
                _LOGGER.warning(
                    "Wartung aktiviert (%s): Automatik inkl. Frostschutz ist deaktiviert.",
                    self.entry.entry_id,
                )
            else:
                new_opts.pop(OPT_KEY_MAINTENANCE_ACTIVE, None)
                _LOGGER.info("Wartung deaktiviert (%s): Automatik läuft wieder.", self.entry.entry_id)
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von Wartungsmodus")

    async def set_hvac_enabled(self, enabled: bool):
        """Enable/disable thermostat behavior (independent from maintenance)."""
        enabled = bool(enabled)
        if enabled == bool(getattr(self, "hvac_enabled", True)):
            return
        self.hvac_enabled = enabled
        try:
            new_opts = {**(self.entry.options or {})}
            if enabled:
                new_opts[OPT_KEY_HVAC_ENABLED] = True
            else:
                new_opts[OPT_KEY_HVAC_ENABLED] = False
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von hvac_enabled")

    async def start_manual_heat_to_target(self):
        """User-triggered heat-to-target: uses the bathing manual timer with an estimated duration."""
        if not self.entry:
            return
        conf = {**(self.entry.data or {}), **(self.entry.options or {})}
        water_temp = self._get_float(conf.get(CONF_TEMP_WATER))
        est = self._estimate_minutes_to_target(conf, water_temp)
        # If we can't estimate, fall back to a sensible default.
        minutes = 60 if est is None else int(est)
        # Clamp to avoid ridiculous durations due to wrong config/sensors.
        minutes = max(1, min(24 * 60, minutes))
        await self.activate_manual_timer(timer_type="bathing", minutes=minutes)

    async def stop_manual_heat(self):
        """Stops user-triggered heating (bathing timer only)."""
        await self.deactivate_manual_timer(only_type="bathing")

    async def set_target_temperature(self, temperature: float):
        """Set and persist the target temperature (setpoint)."""
        try:
            temperature = float(temperature)
        except Exception:
            return
        self.target_temp = temperature
        try:
            new_opts = {**(self.entry.options or {})}
            new_opts[OPT_KEY_TARGET_TEMP] = temperature
            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von target_temp")

    async def _async_update_entry_options(self, options: dict) -> None:
        """Compat wrapper for config entry updates.

        Home Assistant's `async_update_entry` has historically been a callback returning bool
        in some versions, while other versions may return an awaitable.
        """
        if not self.entry:
            return
        res = self.hass.config_entries.async_update_entry(self.entry, options=options)
        if inspect.isawaitable(res):
            await res

    async def _async_turn_entity(self, entity_id: str | None, turn_on: bool) -> None:
        """Best-effort turn_on/turn_off with service fallback.

        Uses the entity's domain service when available, otherwise falls back to
        `homeassistant.turn_on/off` to avoid ServiceNotFound for domains that are not loaded.
        """
        if not entity_id:
            return
        domain = str(entity_id).split(".", 1)[0]
        service = "turn_on" if turn_on else "turn_off"
        call_domain = domain if self.hass.services.has_service(domain, service) else "homeassistant"
        await self.hass.services.async_call(call_domain, service, {"entity_id": entity_id})

    def _thermostat_demand(self, current_temp: float | None, target_temp: float, cold_tolerance: float, hot_tolerance: float, prev_on: bool) -> bool:
        """Simple hysteresis: turn ON below (target-cold), turn OFF at/above (target+hot)."""
        if current_temp is None:
            return False
        try:
            ct = float(current_temp)
            tt = float(target_temp)
            cold = float(cold_tolerance)
            hot = float(hot_tolerance)
        except Exception:
            return prev_on
        if prev_on:
            return ct < (tt + hot)
        return ct < (tt - cold)

    async def _async_update_data(self):
        # Safe defaults used if update cannot complete (avoid exposing None/unset keys)
        _safe_defaults = {
            "should_pump_on": False,
            "should_main_on": False,
            "should_aux_on": False,
        }

        try:
            _LOGGER.debug("Coordinator update start (%s)", getattr(self.entry, "entry_id", None))
            now = dt_util.now()
            conf = {**self.entry.data, **self.entry.options}

            # Ensure aux_enabled is always a boolean (defensive)
            self.aux_enabled = bool(getattr(self, "aux_enabled", False))

            # Physical switch entity IDs (may be external entities). Used for state mirroring.
            main_switch_id = conf.get(CONF_MAIN_SWITCH)
            pump_switch_id = conf.get(CONF_PUMP_SWITCH) or main_switch_id
            aux_switch_id = conf.get(CONF_AUX_HEATING_SWITCH)
            demo = conf.get(CONF_DEMO_MODE, False)

            # Mirror physical switch states (best-effort; unknown/unavailable -> False).
            main_sw_state = self.hass.states.get(main_switch_id) if main_switch_id else None
            pump_sw_state = self.hass.states.get(pump_switch_id) if pump_switch_id else None
            aux_sw_state = self.hass.states.get(aux_switch_id) if aux_switch_id else None
            main_switch_on = bool(main_sw_state and main_sw_state.state == "on")
            pump_switch_on = bool(pump_sw_state and pump_sw_state.state == "on")
            aux_heating_switch_on = bool(aux_sw_state and aux_sw_state.state == "on")

            maintenance_active = bool(conf.get(OPT_KEY_MAINTENANCE_ACTIVE, False))
            # Keep attribute in sync so other entities (e.g. climate) can read it.
            self.maintenance_active = maintenance_active

            # HVAC enabled state (independent from maintenance).
            self.hvac_enabled = bool(conf.get(OPT_KEY_HVAC_ENABLED, True))

            # First run: migrate legacy timer options (best effort)
            await self.async_migrate_legacy_timers()
            
            # Sensoren
            water_temp = self._get_float(conf.get(CONF_TEMP_WATER))
            outdoor_temp = self._get_float(conf.get(CONF_TEMP_OUTDOOR))
            ph_val = self._get_float(conf.get(CONF_PH_SENSOR))
            chlor_val = self._get_float(conf.get(CONF_CHLORINE_SENSOR))
            salt_val = self._get_float(conf.get(CONF_SALT_SENSOR))
            conductivity_val = self._get_float(conf.get(CONF_TDS_SENSOR))  # in μS/cm
            # TDS-Umrechnung: μS/cm * 0.64 = ppm (Standard-Konversionsfaktor)
            tds_val = round(conductivity_val * 0.64) if conductivity_val else None

            # Sanitizer mode affects how we interpret TDS:
            # In saltwater/mixed mode, conductivity/TDS is dominated by salt and would otherwise look "too high".
            # We therefore compute an "effective" TDS (approx. non-salt dissolved solids) by subtracting the
            # configured target salt baseline (g/L -> ppm). This value is used for status and water-change
            # recommendations.
            sanitizer_mode = (conf.get(CONF_SANITIZER_MODE) or "").strip().lower()
            if sanitizer_mode not in ("chlorine", "saltwater", "mixed"):
                sanitizer_mode = "saltwater" if bool(conf.get(CONF_ENABLE_SALTWATER, False)) else DEFAULT_SANITIZER_MODE
            saltwater_mode = sanitizer_mode in ("saltwater", "mixed")
            try:
                target_salt_g_l = float(conf.get(CONF_TARGET_SALT_G_L, DEFAULT_TARGET_SALT_G_L))
            except Exception:
                target_salt_g_l = DEFAULT_TARGET_SALT_G_L
            salt_baseline_ppm = None
            if saltwater_mode and target_salt_g_l and target_salt_g_l > 0:
                salt_baseline_ppm = float(target_salt_g_l) * 1000.0
            tds_effective = None
            if tds_val is not None:
                if salt_baseline_ppm is not None:
                    try:
                        tds_effective = max(0, int(round(float(tds_val) - salt_baseline_ppm)))
                    except Exception:
                        tds_effective = tds_val
                else:
                    tds_effective = tds_val

            # 2. Chemie (Ziel pH 7.2, Toleranzbereich 7.0-7.4)
            vol_f = conf.get(CONF_WATER_VOLUME, DEFAULT_VOL) / 1000
            vol_l = conf.get(CONF_WATER_VOLUME, DEFAULT_VOL)

            # Salz-Empfehlung (nur in saltwater/mixed): benötigte Salzmenge in Gramm
            salt_add_g = 0
            try:
                if saltwater_mode and vol_l and salt_val is not None and target_salt_g_l and target_salt_g_l > 0:
                    missing_g_l = max(0.0, float(target_salt_g_l) - float(salt_val))
                    # g/L * L => g
                    salt_add_g = int(round(missing_g_l * float(vol_l)))
            except Exception:
                salt_add_g = 0
            
            # TDS-Wartung: Status und Wasserwechsel-Empfehlungen
            tds_status = None
            tds_water_change_liters = 0
            tds_water_change_percent = 0
            tds_high = False

            # Use effective TDS for maintenance interpretation (see above).
            tds_for_maintenance = tds_effective if tds_effective is not None else tds_val
            if tds_for_maintenance is not None:
                target_tds = 1200  # Ziel-TDS (nicht-salzige gelöste Stoffe) in ppm
                if tds_for_maintenance < 1500:
                    tds_status = "optimal"
                elif tds_for_maintenance < 2000:
                    tds_status = "good"
                elif tds_for_maintenance < 2500:
                    tds_status = "high"
                    tds_high = True
                elif tds_for_maintenance < 3000:
                    tds_status = "critical"
                    tds_high = True
                else:
                    tds_status = "urgent"
                    tds_high = True
                
                # Wasserwechsel-Berechnung: Liter = Volumen × (TDS_aktuell - Ziel) / TDS_aktuell
                if vol_l and tds_for_maintenance > target_tds:
                    tds_water_change_liters = round(vol_l * (tds_for_maintenance - target_tds) / tds_for_maintenance)
                    tds_water_change_percent = round((tds_water_change_liters / vol_l) * 100)
            
            main_power = self._get_float(conf.get(CONF_MAIN_POWER_SENSOR))
            aux_power = self._get_float(conf.get(CONF_AUX_POWER_SENSOR))
            
            # 1. Frost & Wochenende
            # Frostschutz nur wenn aktiviert UND Outdoor-Sensor vorhanden
            enable_frost = conf.get(CONF_ENABLE_FROST_PROTECTION, True)
            frost_start_temp = conf.get(CONF_FROST_START_TEMP, DEFAULT_FROST_START_TEMP)
            frost_severe_temp = conf.get(CONF_FROST_SEVERE_TEMP, DEFAULT_FROST_SEVERE_TEMP)
            frost_mild_interval = conf.get(CONF_FROST_MILD_INTERVAL, DEFAULT_FROST_MILD_INTERVAL)
            frost_mild_run = conf.get(CONF_FROST_MILD_RUN, DEFAULT_FROST_MILD_RUN)
            frost_severe_interval = conf.get(CONF_FROST_SEVERE_INTERVAL, DEFAULT_FROST_SEVERE_INTERVAL)
            frost_severe_run = conf.get(CONF_FROST_SEVERE_RUN, DEFAULT_FROST_SEVERE_RUN)
            frost_quiet_override_below = conf.get(CONF_FROST_QUIET_OVERRIDE_BELOW_TEMP, DEFAULT_FROST_QUIET_OVERRIDE_BELOW_TEMP)

            try:
                frost_start_temp = float(frost_start_temp)
            except Exception:
                frost_start_temp = DEFAULT_FROST_START_TEMP
            try:
                frost_severe_temp = float(frost_severe_temp)
            except Exception:
                frost_severe_temp = DEFAULT_FROST_SEVERE_TEMP
            try:
                frost_quiet_override_below = float(frost_quiet_override_below)
            except Exception:
                frost_quiet_override_below = DEFAULT_FROST_QUIET_OVERRIDE_BELOW_TEMP

            try:
                frost_mild_interval = int(frost_mild_interval)
            except Exception:
                frost_mild_interval = DEFAULT_FROST_MILD_INTERVAL
            try:
                frost_mild_run = int(frost_mild_run)
            except Exception:
                frost_mild_run = DEFAULT_FROST_MILD_RUN
            try:
                frost_severe_interval = int(frost_severe_interval)
            except Exception:
                frost_severe_interval = DEFAULT_FROST_SEVERE_INTERVAL
            try:
                frost_severe_run = int(frost_severe_run)
            except Exception:
                frost_severe_run = DEFAULT_FROST_SEVERE_RUN

            frost_danger = False
            frost_active = False
            frost_is_severe = False
            frost_run_mins = 0
            ot = None
            if outdoor_temp is not None:
                try:
                    ot = float(outdoor_temp)
                except Exception:
                    ot = None

            if enable_frost and ot is not None and ot < frost_start_temp:
                frost_danger = True
                interval = max(1, frost_mild_interval)
                run_mins = max(0, frost_mild_run)
                if ot <= frost_severe_temp:
                    frost_is_severe = True
                    interval = max(1, frost_severe_interval)
                    run_mins = max(0, frost_severe_run)
                frost_run_mins = run_mins
                # duty-cycle uses epoch minutes to avoid daily "reset" artifacts
                now_local = dt_util.as_local(now)
                epoch_minutes = int(now_local.timestamp() // 60)
                frost_active = (run_mins > 0) and ((epoch_minutes % interval) < run_mins)

            # Frost-Timer: Wenn frost_active, berechne Restlaufzeit und setze Timer-Attribute
            frost_timer_mins = 0
            frost_timer_active = False
            frost_timer_duration = None
            frost_timer_type = None
            if frost_active and frost_danger and frost_run_mins > 0:
                now_local = dt_util.as_local(now)
                epoch_minutes = int(now_local.timestamp() // 60)
                rem = frost_run_mins - (epoch_minutes % max(1, interval))
                frost_timer_mins = max(0, rem)
                frost_timer_active = True
                frost_timer_duration = frost_run_mins
                frost_timer_type = "frost"
                self.frost_timer_until = now + timedelta(minutes=frost_timer_mins)
                self.frost_timer_duration = frost_run_mins
            else:
                self.frost_timer_until = None
                self.frost_timer_duration = None
            is_holiday = await self._check_holiday(conf.get(CONF_HOLIDAY_CALENDAR))
            we_or_holiday = is_holiday or (now.weekday() >= 5)

            # pH-Toleranzbereich: 7.0 - 7.4 (keine Dosierung nötig)
            # Außerhalb: Differenz zu Zielwert 7.2 berechnen
            if ph_val and ph_val > 7.4:
                ph_minus = max(0, round((ph_val - 7.2) * 100 * vol_f))
                ph_plus = 0
            elif ph_val and ph_val < 7.0:
                ph_plus = max(0, round((7.2 - ph_val) * 100 * vol_f))
                ph_minus = 0
            else:
                ph_minus = 0
                ph_plus = 0

            # Chlor/ORP: Zielwert 700 mV, pro 100 mV unter 700 -> 0.25 Löffel (für 1000L)
            # Skalierung mit tatsächlicher Wassermenge.
            # WICHTIG: In reinem Salzwasser-Modus wird kein "Chlor hinzufügen" empfohlen,
            # da die Chlor-Erzeugung über die Salzumwandlung erfolgen soll.
            chlor_spoons = 0
            try:
                if sanitizer_mode in ("chlorine", "mixed") and chlor_val is not None and float(chlor_val) < 700:
                    quarter_spoons = round((700 - float(chlor_val)) / 100)  # Viertellöffel
                    base_spoons = quarter_spoons / 4.0  # Zu Löffeln umrechnen
                    chlor_spoons = round(base_spoons * (vol_l / 1000.0), 2) if vol_l else 0
            except Exception:
                chlor_spoons = 0

            # 3. Kalender & Aufheizzeit
            # Heizleistung ist eine Konstante (W) und darf NICHT aus einem Live-Pumpen-Power-Sensor abgeleitet werden.
            # Sonst wird die Preheat-Berechnung massiv falsch und startet u.U. Tage zu früh.
            power_w = None
            try:
                base_w = int(conf.get(CONF_HEATER_BASE_POWER_W, DEFAULT_HEATER_BASE_POWER_W))
            except Exception:
                base_w = DEFAULT_HEATER_BASE_POWER_W
            try:
                aux_w = int(conf.get(CONF_HEATER_AUX_POWER_W, DEFAULT_HEATER_AUX_POWER_W))
            except Exception:
                aux_w = DEFAULT_HEATER_AUX_POWER_W
            base_w = max(0, int(base_w or 0))
            aux_w = max(0, int(aux_w or 0))

            # Backward compatibility:
            # Older versions used a single `heater_power_w` value.
            # If split values are not configured (both unset/zero), fall back to the legacy value.
            try:
                legacy_present = CONF_HEATER_POWER_W in conf and conf.get(CONF_HEATER_POWER_W) is not None
                split_effective_raw = base_w + aux_w
                if legacy_present and split_effective_raw <= 0:
                    base_w = max(0, int(float(conf.get(CONF_HEATER_POWER_W))))
            except Exception:
                pass

            # Prefer split model if configured to a meaningful value.
            split_effective = base_w + (aux_w if conf.get(CONF_ENABLE_AUX_HEATING, False) else 0)
            if split_effective > 0:
                power_w = split_effective
            else:
                try:
                    power_w = int(conf.get(CONF_HEATER_POWER_W, DEFAULT_HEATER_POWER_W))
                except Exception:
                    power_w = DEFAULT_HEATER_POWER_W

            if not power_w or power_w <= 0:
                power_w = DEFAULT_HEATER_POWER_W

            # Temperaturdifferenz (DeltaT).
            # Wenn Wassertemperatur fehlt, konservativer Default 20°C (statt Fehler)
            measured_temp = water_temp if water_temp is not None else 20.0
            delta_t = max(0.0, self.target_temp - measured_temp)

            # Thermostat-like tolerances (hysteresis)
            try:
                cold_tol = float(conf.get(CONF_COLD_TOLERANCE, DEFAULT_COLD_TOLERANCE))
            except Exception:
                cold_tol = DEFAULT_COLD_TOLERANCE
            try:
                hot_tol = float(conf.get(CONF_HOT_TOLERANCE, DEFAULT_HOT_TOLERANCE))
            except Exception:
                hot_tol = DEFAULT_HOT_TOLERANCE

            heat_time = None
            if vol_l is not None and power_w > 0 and delta_t > 0:
                # t_min in Minuten: V * 1.16 * deltaT / P * 60
                t_min = (vol_l * 1.16 * delta_t) / float(power_w) * 60.0
                try:
                    heat_time = max(0, int(round(t_min)))
                except Exception:
                    heat_time = None

            cal = await self._get_next_event(conf.get(CONF_POOL_CALENDAR))
            cal_next = (cal or {}).get("next") or {}
            cal_ongoing = (cal or {}).get("ongoing") or {}

            # Next start (preheat start): if we can't compute a heat_time (e.g. delta_t == 0 because
            # water is already at/above target), still expose a meaningful countdown to the event.
            # In that case, we treat heat_time as 0 minutes => next_start_mins == minutes until event start.
            next_start_mins = None
            if cal_next.get("start"):
                effective_heat_time = heat_time if heat_time is not None else 0
                preheat_time = cal_next["start"] - timedelta(minutes=effective_heat_time)
                next_start_mins = max(0, round((preheat_time - now).total_seconds() / 60))
            def _mins_left(until_dt: datetime | None):
                if until_dt is None:
                    return 0
                if until_dt <= now:
                    return 0
                return max(0, int(((until_dt - now).total_seconds() + 59) // 60))

            pause_active = self.pause_until is not None and now < self.pause_until

            manual_active = self.manual_timer_until is not None and now < self.manual_timer_until and self.manual_timer_type in ("bathing", "chlorine", "filter")
            manual_mins = _mins_left(self.manual_timer_until) if manual_active else 0

            auto_filter_active = self.auto_filter_until is not None and now < self.auto_filter_until
            auto_filter_mins = _mins_left(self.auto_filter_until) if auto_filter_active else 0
            
            # Initialisiere next_filter_start wenn nicht gesetzt (z.B. nach Neustart)
            if not getattr(self, "next_filter_start", None):
                self.next_filter_start = now + timedelta(minutes=self.filter_interval)

            # PV sensor logic
            enable_pv = conf.get(CONF_ENABLE_PV_OPTIMIZATION, False)
            pv_raw = self._get_float(conf.get(CONF_PV_SURPLUS_SENSOR))
            pv_val = pv_raw if enable_pv else None

            # Compute smoothed PV (exponential moving average) using configured window (seconds).
            try:
                window = int(conf.get(CONF_PV_SMOOTH_WINDOW_SECONDS, getattr(self, 'pv_smooth_window', DEFAULT_PV_SMOOTH_WINDOW_SECONDS)))
            except Exception:
                window = DEFAULT_PV_SMOOTH_WINDOW_SECONDS
            if pv_val is None:
                # No input -> keep previous smoothed value
                pv_smoothed = getattr(self, '_pv_smoothed', None)
            else:
                if getattr(self, '_pv_smoothed', None) is None or not window or window <= 0:
                    pv_smoothed = pv_val
                else:
                    # alpha = min(1, dt / window)
                    try:
                        dt_s = self.update_interval.total_seconds() if getattr(self, 'update_interval', None) else 30
                    except Exception:
                        dt_s = 30
                    alpha = float(min(1.0, float(dt_s) / float(window)))
                    pv_smoothed = float(self._pv_smoothed + alpha * (pv_val - float(self._pv_smoothed)))
            # persist
            self._pv_smoothed = pv_smoothed

            # Stability logic: only flip pv_allows after the smoothed value crosses thresholds
            pv_allows = bool(getattr(self, '_pv_allows_effective', False))
            try:
                on_th = int(conf.get(CONF_PV_ON_THRESHOLD, getattr(self, 'pv_on_threshold', DEFAULT_PV_ON)))
            except Exception:
                on_th = DEFAULT_PV_ON
            try:
                off_th = int(conf.get(CONF_PV_OFF_THRESHOLD, getattr(self, 'pv_off_threshold', DEFAULT_PV_OFF)))
            except Exception:
                off_th = DEFAULT_PV_OFF

            desired = None
            if pv_smoothed is not None:
                if pv_smoothed >= on_th:
                    desired = True
                elif pv_smoothed <= off_th:
                    desired = False
            # Stability window (seconds)
            try:
                stability = int(conf.get(CONF_PV_STABILITY_SECONDS, getattr(self, 'pv_stability_seconds', DEFAULT_PV_STABILITY_SECONDS)))
            except Exception:
                stability = DEFAULT_PV_STABILITY_SECONDS
            now_dt = now
            # Candidate handling
            if desired is None:
                # no definitive crossing -> do not change candidate timer
                pass
            else:
                if desired != pv_allows:
                    # Start candidate timer if not set
                    if not getattr(self, '_pv_candidate_since', None):
                        self._pv_candidate_since = now_dt
                    else:
                        # If candidate lasted long enough, commit change
                        if (now_dt - self._pv_candidate_since).total_seconds() >= stability:
                            # If turning ON -> commit and record start time
                            if desired:
                                pv_allows = True
                                self._pv_last_start = now_dt
                                self._pv_allows_effective = True
                                self._pv_candidate_since = None
                            else:
                                # Turning OFF: respect minimum run minutes if set
                                try:
                                    min_run = int(conf.get(CONF_PV_MIN_RUN_MINUTES, getattr(self, 'pv_min_run_minutes', DEFAULT_PV_MIN_RUN_MINUTES)))
                                except Exception:
                                    min_run = DEFAULT_PV_MIN_RUN_MINUTES
                                if self._pv_last_start and (now_dt - self._pv_last_start).total_seconds() < (min_run * 60):
                                    # not enough run time yet; keep pv_allows True and continue waiting
                                    pv_allows = True
                                    # keep candidate_since to re-evaluate later
                                else:
                                    pv_allows = False
                                    self._pv_allows_effective = False
                                    self._pv_candidate_since = None
                else:
                    # desired == pv_allows -> clear candidate if any
                    self._pv_candidate_since = None
            # quiet time check: C and E should not activate during quiet; A/B/D always allowed
            def _in_quiet_period(cfg):
                try:
                    now_local = dt_util.as_local(now)
                    t = now_local.time()
                    weekday = now_local.weekday()
                    if weekday >= 5 or is_holiday:
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

            def _next_quiet_start(cfg):
                """Returns the next quiet-start datetime in local time, based on today's weekday/holiday settings."""
                try:
                    now_local = dt_util.as_local(now)
                    t = now_local.time()
                    weekday = now_local.weekday()
                    if weekday >= 5 or is_holiday:
                        start_s = cfg.get(CONF_QUIET_START_WEEKEND, DEFAULT_Q_START_WE)
                        end_s = cfg.get(CONF_QUIET_END_WEEKEND, DEFAULT_Q_END_WE)
                    else:
                        start_s = cfg.get(CONF_QUIET_START, DEFAULT_Q_START)
                        end_s = cfg.get(CONF_QUIET_END, DEFAULT_Q_END)

                    start_t = dt_util.parse_time(start_s)
                    end_t = dt_util.parse_time(end_s)
                    if start_t is None or end_t is None:
                        return None

                    start_today = now_local.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
                    start_tomorrow = (now_local + timedelta(days=1)).replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)

                    if start_t <= end_t:
                        # same-day window
                        if t < start_t:
                            return start_today
                        if t > end_t:
                            return start_tomorrow
                        # currently in quiet
                        return start_today

                    # overnight window
                    # not-in-quiet means we're between end_t and start_t (daytime)
                    if t < start_t and t > end_t:
                        return start_today
                    # in quiet -> next start is later today (morning case) or already started (evening case)
                    return start_today if t <= end_t else start_tomorrow
                except Exception:
                    return None

            def _quiet_times_for(dt_obj, cfg):
                dt_local = dt_util.as_local(dt_obj)
                weekday = dt_local.weekday()
                if weekday >= 5:
                    start_s = cfg.get(CONF_QUIET_START_WEEKEND, DEFAULT_Q_START_WE)
                    end_s = cfg.get(CONF_QUIET_END_WEEKEND, DEFAULT_Q_END_WE)
                else:
                    start_s = cfg.get(CONF_QUIET_START, DEFAULT_Q_START)
                    end_s = cfg.get(CONF_QUIET_END, DEFAULT_Q_END)
                return dt_util.parse_time(start_s), dt_util.parse_time(end_s)

            def _is_in_quiet_at(dt_obj, cfg):
                try:
                    dt_local = dt_util.as_local(dt_obj)
                    t = dt_local.time()
                    start_t, end_t = _quiet_times_for(dt_obj, cfg)
                    if start_t <= end_t:
                        return start_t <= t <= end_t
                    return t >= start_t or t <= end_t
                except Exception:
                    return False

            def _quiet_end_for(dt_obj, cfg):
                dt_local = dt_util.as_local(dt_obj)
                start_t, end_t = _quiet_times_for(dt_obj, cfg)
                end_today = dt_local.replace(hour=end_t.hour, minute=end_t.minute, second=0, microsecond=0)
                end_tomorrow = (dt_local + timedelta(days=1)).replace(hour=end_t.hour, minute=end_t.minute, second=0, microsecond=0)

                if start_t <= end_t:
                    # same-day window
                    return end_today if dt_local <= end_today else end_tomorrow

                # overnight window
                if dt_local.time() >= start_t:
                    return end_tomorrow
                if dt_local.time() <= end_t:
                    return end_today
                return end_tomorrow

            in_quiet = _in_quiet_period(conf)

            # =========================
            # Next frost run (best-effort)
            # =========================
            next_frost_mins = None
            try:
                enable_frost_effective = bool(enable_frost and (ot is not None) and (ot < frost_start_temp) and (not maintenance_active) and (frost_run_mins > 0))
                if enable_frost_effective:
                    # If frost is currently suppressed by quiet hours (unless extremely cold), skip to the end of quiet.
                    if in_quiet and (ot is not None) and (ot > frost_quiet_override_below):
                        qe = _quiet_end_for(now, conf)
                        if qe is not None:
                            mins_to_qe = max(0, int(((qe - now).total_seconds() + 59) // 60))
                            qe_local = dt_util.as_local(qe)
                            epoch_minutes_qe = int(qe_local.timestamp() // 60)
                            rem = epoch_minutes_qe % max(1, int(interval))
                            if rem < frost_run_mins:
                                next_frost_mins = mins_to_qe
                            else:
                                next_frost_mins = mins_to_qe + (max(1, int(interval)) - rem)
                    else:
                        now_local = dt_util.as_local(now)
                        epoch_minutes = int(now_local.timestamp() // 60)
                        rem = epoch_minutes % max(1, int(interval))
                        # We only show the next start when we are currently NOT running.
                        if not frost_active:
                            next_frost_mins = max(0, max(1, int(interval)) - rem)
            except Exception:
                next_frost_mins = None

            # Wartung = Hard-Lockout: keine Automatik-Aktionen (auch kein Frostschutz)
            if maintenance_active:
                frost_active = False

            # Optional optimization: In severe frost, force one run shortly before quiet hours start
            # (quiet_start - frost_run_mins .. quiet_start). This reduces the chance of needing runs inside quiet hours.
            if frost_danger and frost_is_severe and (not in_quiet) and frost_run_mins > 0:
                qs = _next_quiet_start(conf)
                if qs is not None:
                    mins_to_qs = (qs - now).total_seconds() / 60
                    if 0 <= mins_to_qs <= frost_run_mins:
                        frost_active = True

            # Ruhezeit ist heilig: Frostschutz darf sie nur im "äußersten Notfall" stören.
            # => Während Ruhezeit nur aktiv, wenn Außentemp <= frost_quiet_override_below
            if in_quiet and ot is not None and ot > frost_quiet_override_below:
                frost_active = False

            # Wenn der geplante Filter-Start in eine Ruhezeit fällt: vorab auf das Ruhezeit-Ende verschieben.
            enable_auto_filter = conf.get(CONF_ENABLE_AUTO_FILTER, True)
            if enable_auto_filter and getattr(self, "next_filter_start", None) and _is_in_quiet_at(self.next_filter_start, conf):
                shifted = _quiet_end_for(self.next_filter_start, conf)
                if shifted:
                    # Make sure the scheduled start is strictly after the quiet period end
                    # to avoid edge cases where the computed time equals or falls
                    # marginally before the quiet end (off-by-one minute issues).
                    try:
                        shifted = shifted + timedelta(seconds=1)
                    except Exception:
                        # Best-effort: if timedelta fails for any reason, keep shifted as-is
                        pass
                    if shifted != self.next_filter_start:
                        self.next_filter_start = shifted
                        try:
                            new_opts = {**self.entry.options, OPT_KEY_FILTER_NEXT: shifted.isoformat()}
                            await self._async_update_entry_options(new_opts)
                        except Exception:
                            _LOGGER.exception("Fehler beim Verschieben von next_filter_start (Ruhezeit)")

            next_filter_mins = None
            if getattr(self, "next_filter_start", None):
                next_filter_mins = max(0, round((self.next_filter_start - now).total_seconds() / 60))

            # Start calendar-driven bathing: if event is ongoing, ensure manual timer active
            # (in Wartung deaktiviert)
            if (not maintenance_active) and cal_ongoing.get("start") and cal_ongoing.get("end"):
                if now >= cal_ongoing["start"] and now < cal_ongoing["end"]:
                    remaining_min = max(1, int((cal_ongoing["end"] - now).total_seconds() / 60))
                    if (not pause_active) and (not manual_active):
                        await self.activate_manual_timer(timer_type="bathing", minutes=remaining_min)
                        # recompute
                        manual_active = self.manual_timer_until is not None and now < self.manual_timer_until and self.manual_timer_type in ("bathing", "chlorine", "filter")
                        manual_mins = _mins_left(self.manual_timer_until) if manual_active else 0

            # Auto-start filter when next_filter_start reached (in Wartung deaktiviert)
            # Debug: if the scheduled time is reached but auto-start is skipped, log why.
            if getattr(self, "next_filter_start", None) and now >= self.next_filter_start:
                reasons = []
                if maintenance_active:
                    reasons.append("maintenance_active")
                if not enable_auto_filter:
                    reasons.append("auto_filter_disabled")
                if auto_filter_active:
                    reasons.append("auto_filter_already_active")
                if pause_active:
                    reasons.append("pause_active")
                if in_quiet:
                    reasons.append("in_quiet")
                # Note: PV should not block scheduled filter starts anymore, so we do not
                # append a pv_not_allowed reason here. Filtering will run regardless of PV
                # availability unless suppressed by maintenance/pause/quiet.
                if reasons:
                    _LOGGER.debug(
                        "Auto-filter time reached but skipped: %s -- flags maintenance=%s enable_auto_filter=%s auto_filter_active=%s pause=%s in_quiet=%s next_filter_start=%s now=%s",
                        ", ".join(reasons),
                        maintenance_active,
                        enable_auto_filter,
                        auto_filter_active,
                        pause_active,
                        in_quiet,
                        getattr(self, "next_filter_start", None),
                        now,
                    )

            # Auto-start filter when next_filter_start reached (in Wartung deaktiviert)
            # NOTE: Filtering (auto or manual) must run regardless of PV surplus.
            # Previously this branch could be skipped when PV optimization was enabled
            # but no PV surplus was present. Adjust logic to always start the auto-filter
            # when scheduled unless suppressed by quiet hours / maintenance / pause.
            if (not maintenance_active) and enable_auto_filter and getattr(self, "next_filter_start", None) and now >= self.next_filter_start and (not auto_filter_active) and (not pause_active):
                if in_quiet:
                    shifted = _quiet_end_for(now, conf)
                    if shifted and shifted != self.next_filter_start:
                        self.next_filter_start = shifted
                        try:
                            new_opts = {**self.entry.options, OPT_KEY_FILTER_NEXT: shifted.isoformat()}
                            await self._async_update_entry_options(new_opts)
                        except Exception:
                            _LOGGER.exception("Fehler beim Umplanen von next_filter_start (Ruhezeit, fällig)")
                else:
                    # Always start auto-filter when due (PV should not block filtering)
                    await self._start_auto_filter(minutes=self.filter_minutes)
                    auto_filter_active = self.auto_filter_until is not None and now < self.auto_filter_until
                    auto_filter_mins = _mins_left(self.auto_filter_until) if auto_filter_active else 0

            # Convenience booleans for logic

            # Initialisierung, um UnboundLocalError zu vermeiden
            is_bathing = False
            is_chlorinating = False
            is_manual_filter = False
            is_manual_heat = False
            if manual_active and self.manual_timer_type is not None:
                is_bathing = self.manual_timer_type == "bathing"
                is_chlorinating = self.manual_timer_type == "chlorine"
                is_manual_filter = self.manual_timer_type == "filter"
                is_manual_heat = self.manual_timer_type in ("bathing", "chlorine", "filter")

            # PV-based run should stop once target is reached (with same hysteresis).
            try:
                if water_temp is not None and float(water_temp) >= float(self.target_temp):
                    pv_heat_demand = False
                else:
                    pv_heat_demand = self._thermostat_demand(
                        current_temp=water_temp,
                        target_temp=self.target_temp,
                        cold_tolerance=cold_tol,
                        hot_tolerance=hot_tol,
                        prev_on=bool(self._pv_heat_demand),
                    )
            except Exception:
                pv_heat_demand = bool(self._pv_heat_demand)
            self._pv_heat_demand = pv_heat_demand
            pv_run = bool(enable_pv and pv_allows and (not in_quiet) and (not maintenance_active) and (pv_heat_demand))

            # Optimiert: manuelle Timer erzwingen "heat"-Modus
            manual_heat_run = is_manual_heat


            # "Preheat" ist nur die Phase VOR einem Kalender-Event, in der wir bereits starten dürfen.
            # Wenn das Event bereits läuft, wird oben automatisch ein bathing-Manual-Timer aktiviert.
            preheat_active = bool(
                (next_start_mins is not None and next_start_mins == 0)
                and cal_next.get("start")
                and now < cal_next["start"]
            )


            # Thermostat behavior: if PV optimization is disabled, allow heating to maintain target temperature
            # (similar to a normal climate entity), gated by hvac_enabled.
            thermostat_run = bool((not enable_pv) and getattr(self, "hvac_enabled", True))

            # NEU: heat_allowed auch bei manueller Filterung/Chloring
            heat_allowed = (not maintenance_active) and (not pause_active) and (not in_quiet) and (
                is_bathing
                or preheat_active
                or pv_run
                or thermostat_run
                or manual_heat_run
            )


            # Demand flags
            aux_heat_demand = False
            if heat_allowed and conf.get(CONF_ENABLE_AUX_HEATING, False):
                # Aux heater is strictly for heating. Once target is reached, keep it OFF
                # even if a manual timer (e.g. bathing/filter/chlorine) is active.
                try:
                    if water_temp is not None and float(water_temp) >= float(self.target_temp):
                        aux_heat_demand = False
                    else:
                        aux_heat_demand = self._thermostat_demand(
                            current_temp=water_temp,
                            target_temp=self.target_temp,
                            cold_tolerance=cold_tol,
                            hot_tolerance=hot_tol,
                            prev_on=bool(self._aux_heat_demand),
                        )
                except Exception:
                    aux_heat_demand = bool(self._aux_heat_demand)
            # Bei manueller Filterung oder Chlorung darf die Zusatzheizung
            # nur laufen, wenn gleichzeitig PV-basierter Heizbedarf vorhanden ist.
            if (is_manual_filter or is_chlorinating) and not pv_run:
                aux_heat_demand = False

            self._aux_heat_demand = aux_heat_demand


            # Transparenz: Warum läuft der Pool (Main/Pumpe) gerade?
            if maintenance_active:
                run_reason = "maintenance"
            elif frost_active:
                run_reason = "frost"
            elif pause_active:
                run_reason = "pause"
            elif is_bathing:
                run_reason = "bathing"
            elif is_chlorinating:
                run_reason = "chlorine"
            elif is_manual_filter:
                run_reason = "filter"
            elif (auto_filter_active and (not in_quiet)):
                run_reason = "filter"
            elif preheat_active:
                run_reason = "preheat"
            elif pv_run:
                run_reason = "pv"
            else:
                run_reason = "idle"


            # Transparenz: Warum darf/soll die Heizung laufen?
            if not conf.get(CONF_ENABLE_AUX_HEATING, False):
                heat_reason = "disabled"
            elif heat_allowed:
                if is_bathing:
                    heat_reason = "bathing"
                elif is_manual_filter:
                    heat_reason = "filter"
                elif is_chlorinating:
                    heat_reason = "chlorine"
                elif preheat_active:
                    heat_reason = "preheat"
                elif pv_run:
                    heat_reason = "pv"
                elif thermostat_run:
                    heat_reason = "thermostat"
                else:
                    heat_reason = "off"
            else:
                heat_reason = "off"

            data = {
                "sanitizer_mode": sanitizer_mode,
                "maintenance_active": maintenance_active,
                "run_reason": run_reason,
                "heat_reason": heat_reason,
                "water_temp": round(water_temp, 1) if water_temp is not None else None,
                "outdoor_temp": round(outdoor_temp, 1) if outdoor_temp is not None else None,
                "ph_val": round(ph_val, 2) if ph_val is not None else None,
                "chlor_val": int(chlor_val) if chlor_val is not None else None,
                "salt_val": round(salt_val, 1) if salt_val is not None else None,
                "salt_add_g": salt_add_g,
                "tds_val": tds_val,
                "tds_effective": tds_effective,
                "tds_status": tds_status,
                "tds_high": tds_high,
                "tds_water_change_liters": tds_water_change_liters,
                "tds_water_change_percent": tds_water_change_percent,
                "ph_minus_g": ph_minus,
                "ph_plus_g": ph_plus,
                "chlor_spoons": chlor_spoons,
                "is_we_holiday": we_or_holiday,
                "frost_danger": frost_danger,
                "frost_active": frost_active,
                "next_frost_mins": next_frost_mins,
                # Frost-Timer analog zu manual/auto_filter/pause
                "frost_timer_mins": frost_timer_mins,
                "frost_timer_active": frost_timer_active,
                "frost_timer_duration": frost_timer_duration,
                "frost_timer_type": frost_timer_type,
                "next_event": cal_next.get("start"),
                "next_event_end": cal_next.get("end"),
                "next_event_summary": cal_next.get("summary"),
                "next_start_mins": next_start_mins,
                # Timers: states are remaining minutes
                "manual_timer_mins": manual_mins,
                "manual_timer_active": manual_active,
                "auto_filter_timer_mins": auto_filter_mins,
                "auto_filter_timer_active": auto_filter_active,
                "pause_timer_mins": _mins_left(self.pause_until) if pause_active else 0,
                "pause_timer_active": pause_active,
                "is_bathing": is_bathing,
                "next_filter_mins": next_filter_mins,
                # PV power reading (W) - used for UI display/more-info in the dashboard card
                "pv_power": pv_raw,
                "pv_smoothed": round(pv_smoothed, 1) if pv_smoothed is not None else None,
                "pv_allows": pv_allows,
                "in_quiet": in_quiet,
                "main_power": round(main_power, 1) if main_power is not None else None,
                "aux_power": round(aux_power, 1) if aux_power is not None else None,
                # Stromversorgung an, wenn der Pool laufen muss (inkl. Frost) oder wenn die Pumpe laufen soll.
                "should_pump_on": (
                    (not maintenance_active)
                    and (
                        frost_active
                        or (not pause_active and (
                            is_bathing
                            or is_chlorinating
                            or aux_heat_demand
                            or (is_manual_filter and not in_quiet)
                            or (auto_filter_active and not in_quiet)
                            or (next_start_mins is not None and next_start_mins == 0)
                            or pv_run
                        ))
                    )
                ),
                "should_main_on": (
                    (not maintenance_active)
                    and (
                        frost_active
                        or (not pause_active and (
                            is_bathing
                            or is_chlorinating
                            or aux_heat_demand
                            or (is_manual_filter and not in_quiet)
                            or (auto_filter_active and not in_quiet)
                            or (next_start_mins is not None and next_start_mins == 0)
                            or pv_run
                        ))
                    )
                ),
                # Aux-Heizung einschalten, wenn aktiviert UND Temperatur signifikant unter Ziel liegt
                "should_aux_on": (
                    (not maintenance_active)
                    and conf.get(CONF_ENABLE_AUX_HEATING, False)
                    and aux_heat_demand
                ),

                # Physical switch states (mirror the configured external switches).
                # These are *not* the desired/required states; they reflect what is currently ON.
                "main_switch_on": main_switch_on,
                "pump_switch_on": pump_switch_on,
                "aux_heating_switch_on": aux_heating_switch_on,
            }

            # After computing desired states, ensure physical switches follow the desired state
            try:
                desired_main = data.get("should_main_on")
                desired_pump = data.get("should_pump_on")
                desired_aux = data.get("should_aux_on")
                # Debounce / retry guard: avoid rapid repeated attempts for the same entity
                now = dt_util.now()
                min_retry = timedelta(seconds=getattr(self, "toggle_debounce_seconds", DEFAULT_TOGGLE_DEBOUNCE_SECONDS))

                # access entity registry once for source checks
                try:
                    ent_reg = er.async_get(self.hass)
                except Exception:
                    ent_reg = None

                def _is_available(entity_id: str) -> bool:
                    if not entity_id:
                        return False
                    st = self.hass.states.get(entity_id)
                    return bool(st and st.state not in ("unknown", "unavailable"))

                def _is_integration_entity(entity_id: str) -> bool:
                    if not entity_id or not ent_reg:
                        return False
                    try:
                        ent = ent_reg.async_get(entity_id)
                        return bool(ent and ent.config_entry_id == getattr(self.entry, "entry_id", None))
                    except Exception:
                        return False

                def _can_attempt(entity_id: str) -> bool:
                    # No entity configured -> nothing to attempt (caller should handle)
                    if not entity_id:
                        return True
                    # Avoid toggling entities that were created by this integration (would cause feedback loops)
                    if _is_integration_entity(entity_id):
                        _LOGGER.debug("Skipping toggle for %s: entity created by this integration (avoid recursion)", entity_id)
                        return False
                    # Do not attempt when entity is unavailable/unknown
                    if not _is_available(entity_id):
                        _LOGGER.warning("Skipping toggle for %s: entity not available", entity_id)
                        return False
                    last = self._last_toggle_attempts.get(entity_id)
                    if last and (now - last) < min_retry:
                        _LOGGER.warning(
                            "Skipping toggle for %s: last attempt %s seconds ago",
                            entity_id,
                            int((now - last).total_seconds()),
                        )
                        return False
                    return True

                # Toggle main switch according to desired state
                if desired_main != self._last_should_main_on:
                    if desired_main:
                        if not demo and main_switch_id and _can_attempt(main_switch_id):
                            # record attempt timestamp to avoid immediate retries
                            self._last_toggle_attempts[main_switch_id] = now
                            await self._async_turn_entity(main_switch_id, True)
                    else:
                        # don't turn off main while bathing
                        if (maintenance_active or not is_bathing) and not demo and main_switch_id and _can_attempt(main_switch_id):
                            self._last_toggle_attempts[main_switch_id] = now
                            await self._async_turn_entity(main_switch_id, False)
                    self._last_should_main_on = desired_main

                # Toggle pump switch (may be same as main switch)
                if pump_switch_id and pump_switch_id != main_switch_id:
                    if desired_pump != self._last_should_pump_on:
                        if desired_pump:
                            if not demo and _can_attempt(pump_switch_id):
                                self._last_toggle_attempts[pump_switch_id] = now
                                await self._async_turn_entity(pump_switch_id, True)
                        else:
                            if (maintenance_active or not is_bathing) and not demo and _can_attempt(pump_switch_id):
                                self._last_toggle_attempts[pump_switch_id] = now
                                await self._async_turn_entity(pump_switch_id, False)
                        self._last_should_pump_on = desired_pump
                else:
                    # Keep in sync when both are the same underlying entity
                    self._last_should_pump_on = desired_main

                # Toggle aux switch according to desired_aux AND aux_enabled
                # aux_enabled ist der Master-Enable: wenn False, bleibt physischer Schalter immer aus
                if aux_switch_id:
                    physical_aux_should_be_on = desired_aux and self.aux_enabled
                    if physical_aux_should_be_on != self._last_should_aux_on:
                        if physical_aux_should_be_on:
                            if not demo and _can_attempt(aux_switch_id):
                                self._last_toggle_attempts[aux_switch_id] = now
                                await self._async_turn_entity(aux_switch_id, True)
                        else:
                            if not demo and _can_attempt(aux_switch_id):
                                self._last_toggle_attempts[aux_switch_id] = now
                                await self._async_turn_entity(aux_switch_id, False)
                        self._last_should_aux_on = physical_aux_should_be_on
            except Exception:
                _LOGGER.exception("Fehler beim Anwenden der gewünschten Schaltzustände")

            _LOGGER.debug(
                "Coordinator update success (%s) run_reason=%s should_main=%s should_aux=%s",
                getattr(self.entry, "entry_id", None),
                data.get("run_reason"),
                data.get("should_main_on"),
                data.get("should_aux_on"),
            )

            # Defensive: ensure critical boolean keys are present and normalized
            for _k in ("should_pump_on", "should_main_on", "should_aux_on"):
                data[_k] = bool(data.get(_k))

            # Cache last good data for fallback
            self.data = data
            _LOGGER.debug("Coordinator cached data updated (%s)", getattr(self.entry, "entry_id", None))
            return data
        except Exception as err:
            # Prefer to keep last known good data to avoid entities becoming
            # unavailable on transient errors (reduces UI/sensor flapping).
            try:
                _LOGGER.exception("Update Error (using cached data if available): %s", err)
            except Exception:
                _LOGGER.error("Update Error: %s", err)

            # If we have previously cached data, return it instead of raising
            # UpdateFailed so HA doesn't mark entities unavailable.
            # If we have previously cached data, return it instead of raising
            if getattr(self, "data", None):
                _LOGGER.warning(
                    "Returning cached coordinator.data for %s after transient error",
                    getattr(self.entry, "entry_id", None),
                )
                return self.data

            # No cached data available: return safe defaults to avoid immediate entity unavailability
            _LOGGER.warning(
                "No cached coordinator.data available for %s; returning safe defaults",
                getattr(self.entry, "entry_id", None),
            )
            # also persist so subsequent failures return this
            self.data = _safe_defaults
            return self.data

    def _get_float(self, eid):
        if not eid:
            return None
        state = self.hass.states.get(eid)
        if not state:
            return None
        raw = state.state
        if raw in ("unknown", "unavailable", None):
            return None

        # Fast path: already a plain numeric string
        try:
            return float(raw)
        except Exception:
            pass

        # More robust parsing: allow commas and strip units (best effort).
        try:
            s = str(raw).strip()
            s = s.replace(",", ".")
            # Keep digits, sign, decimal point, exponent (e/E)
            s = re.sub(r"[^0-9eE+\-\.]", "", s)
            return float(s) if s else None
        except Exception:
            return None

    async def _check_holiday(self, cal_id):
        if not cal_id: return False
        try:
            res = await self.hass.services.async_call("calendar", "get_events", {"entity_id": cal_id, "start_date_time": dt_util.now().replace(hour=0, minute=0), "end_date_time": dt_util.now().replace(hour=23, minute=59)}, blocking=True, return_response=True)
            return len(res.get(cal_id, {}).get("events", [])) > 0
        except: return False

    async def _get_next_event(self, cal_id):
        if not cal_id:
            return {}

        try:
            now = dt_util.now()
            res = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": cal_id,
                    "start_date_time": now,
                    "end_date_time": now + timedelta(days=7),
                },
                blocking=True,
                return_response=True,
            )
            raw_events = res.get(cal_id, {}).get("events", [])
            if not raw_events:
                return {}

            parsed = []
            for ev in raw_events:
                start_raw = ev.get("start")
                end_raw = ev.get("end")
                start = dt_util.parse_datetime(start_raw) if start_raw else None
                end = dt_util.parse_datetime(end_raw) if end_raw else None
                if not start:
                    continue
                # Normalize to UTC (dt_util.now() is UTC-aware).
                try:
                    start_utc = dt_util.as_utc(start)
                except Exception:
                    start_utc = start
                end_utc = None
                if end:
                    try:
                        end_utc = dt_util.as_utc(end)
                    except Exception:
                        end_utc = end

                parsed.append({
                    "start": start_utc,
                    "end": end_utc,
                    "summary": ev.get("summary", ""),
                })

            if not parsed:
                return {}

            # Prefer the next future event (start >= now). This avoids showing 0 minutes
            # just because an overlapping/all-day event is included in the result window.
            future = [e for e in parsed if e.get("start") and e["start"] >= now]
            future.sort(key=lambda e: e["start"])
            next_ev = future[0] if future else None

            # Still keep track of an ongoing event (start <= now < end) for auto-start bathing.
            ongoing = [e for e in parsed if e.get("start") and e.get("end") and e["start"] <= now < e["end"]]
            ongoing.sort(key=lambda e: e.get("end") or e.get("start"))
            ongoing_ev = ongoing[0] if ongoing else None

            def _compact(e):
                if not e:
                    return {}
                # Keep keys stable; omit empty summary.
                out = {"start": e.get("start"), "end": e.get("end")}
                if e.get("summary"):
                    out["summary"] = e.get("summary")
                return out

            return {"next": _compact(next_ev), "ongoing": _compact(ongoing_ev)}
        except Exception:
            return {}