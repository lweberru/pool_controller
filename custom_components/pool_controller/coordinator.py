import logging
import re
import inspect
import asyncio
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
        # Master-Enable für Zusatzheizung (aux allowed): vom gemergten config/options lesen (default: False)
        try:
            merged = {**(entry.data or {}), **(entry.options or {})} if entry else {}
            self.aux_allowed = bool(merged.get(CONF_ENABLE_AUX_HEATING, False))
            # Backward-compatible alias (legacy internal name)
            self.aux_enabled = self.aux_allowed
        except Exception:
            self.aux_allowed = False
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
        # Away mode (reduced activity)
        self.away_active = False
        self.away_temp = DEFAULT_AWAY_TEMP
        if entry:
            try:
                merged = {**(entry.data or {}), **(entry.options or {})}
                if merged.get(CONF_AWAY_TEMP) is not None:
                    self.away_temp = float(merged.get(CONF_AWAY_TEMP))
            except Exception:
                self.away_temp = DEFAULT_AWAY_TEMP
        # Internal demand states (hysteresis)
        self._aux_heat_demand = False
        self._pv_heat_demand = False
        # PV smoothing / stability internal state
        self._pv_smoothed = None
        self._pv_allows_effective = False
        self._pv_candidate_since = None
        self._pv_last_start = None
        # Weather forecast cache (for calendar weather guard)
        self._weather_forecast_cache = {
            "entity_id": None,
            "fetched_at": None,
            "forecast": None,
        }
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

        # Run credit / merge optimization tracking
        self._credit_last_update = None
        self._credit_streak_source = None
        self._credit_streak_minutes = 0.0
        self._filter_credit_minutes = 0.0
        self._filter_credit_expires_at = None
        self._frost_credit_minutes = 0.0
        self._frost_credit_expires_at = None
        self._last_credit_source = None
        self._last_credit_minutes = 0.0
        self._last_run_active = False
        self._last_run_source = None
        self._last_run_end = None
        self._credit_persist_last_saved = None
        self._credit_persist_snapshot = None

        # Adaptive heating tuning
        self.heat_loss_w_per_c = DEFAULT_HEAT_LOSS_W_PER_C
        self.heat_startup_offset_minutes = DEFAULT_HEAT_STARTUP_OFFSET_MINUTES
        self._last_temp_ts = None
        self._last_temp_value = None
        self._heat_start_ts = None
        self._heat_start_temp = None
        self._heat_start_reached = False
        self._last_heat_active = False
        self._heat_tuning_last_saved = None

        # Derived energy aggregation (month/year from daily sensors)
        self._derived_grid_daily_last_value = None
        self._derived_grid_daily_last_date = None
        self._derived_grid_month_total = 0.0
        self._derived_grid_year_total = 0.0
        self._derived_grid_month_id = None
        self._derived_grid_year_id = None

        self._derived_solar_daily_last_value = None
        self._derived_solar_daily_last_date = None
        self._derived_solar_month_total = 0.0
        self._derived_solar_year_total = 0.0
        self._derived_solar_month_id = None
        self._derived_solar_year_id = None

        self._derived_energy_last_saved = None
        self._derived_energy_snapshot = None

        # Cost accumulation (time-weighted tariffs, daily reset)
        self._cost_daily_last_grid_kwh = None
        self._cost_daily_last_solar_kwh = None
        self._cost_daily_date = None
        self._cost_daily_accum = 0.0
        self._cost_daily_feed_in_loss_accum = 0.0
        self._cost_daily_pv_credit_accum = 0.0
        self._cost_last_tick_at = None
        # Net daily cost tracking (non-decreasing within day)
        self._cost_net_daily_last_value = None
        self._cost_net_daily_date = None
        self._cost_persist_last_saved = None
        self._cost_persist_snapshot = None

        # Derived cost aggregation (month/year from daily cost)
        self._derived_cost_daily_last_value = None
        self._derived_cost_daily_last_date = None
        self._derived_cost_month_total = 0.0
        self._derived_cost_year_total = 0.0
        self._derived_cost_month_id = None
        self._derived_cost_year_id = None

        self._derived_cost_net_daily_last_value = None
        self._derived_cost_net_daily_last_date = None
        self._derived_cost_net_month_total = 0.0
        self._derived_cost_net_year_total = 0.0
        self._derived_cost_net_month_id = None
        self._derived_cost_net_year_id = None
        self._derived_cost_last_saved = None
        self._derived_cost_snapshot = None

        self._did_migrate_timers = False
        if entry and entry.options:
            self.maintenance_active = bool(entry.options.get(OPT_KEY_MAINTENANCE_ACTIVE, False))
            self.hvac_enabled = bool(entry.options.get(OPT_KEY_HVAC_ENABLED, True))
            self.away_active = bool(entry.options.get(OPT_KEY_AWAY_ACTIVE, False))
            # Adaptive tuning persisted values (best effort)
            try:
                if entry.options.get(OPT_KEY_HEAT_LOSS_W_PER_C) is not None:
                    self.heat_loss_w_per_c = float(entry.options.get(OPT_KEY_HEAT_LOSS_W_PER_C))
            except Exception:
                self.heat_loss_w_per_c = DEFAULT_HEAT_LOSS_W_PER_C
            try:
                if entry.options.get(OPT_KEY_HEAT_STARTUP_OFFSET_MINUTES) is not None:
                    self.heat_startup_offset_minutes = float(entry.options.get(OPT_KEY_HEAT_STARTUP_OFFSET_MINUTES))
            except Exception:
                self.heat_startup_offset_minutes = DEFAULT_HEAT_STARTUP_OFFSET_MINUTES
            # Derived energy aggregation (best effort)
            try:
                if entry.options.get(OPT_KEY_DERIVED_GRID_DAILY_LAST_VALUE) is not None:
                    self._derived_grid_daily_last_value = float(entry.options.get(OPT_KEY_DERIVED_GRID_DAILY_LAST_VALUE))
            except Exception:
                self._derived_grid_daily_last_value = None
            try:
                self._derived_grid_daily_last_date = entry.options.get(OPT_KEY_DERIVED_GRID_DAILY_LAST_DATE) or None
            except Exception:
                self._derived_grid_daily_last_date = None
            try:
                if entry.options.get(OPT_KEY_DERIVED_GRID_MONTH_TOTAL) is not None:
                    self._derived_grid_month_total = float(entry.options.get(OPT_KEY_DERIVED_GRID_MONTH_TOTAL))
            except Exception:
                self._derived_grid_month_total = 0.0
            try:
                if entry.options.get(OPT_KEY_DERIVED_GRID_YEAR_TOTAL) is not None:
                    self._derived_grid_year_total = float(entry.options.get(OPT_KEY_DERIVED_GRID_YEAR_TOTAL))
            except Exception:
                self._derived_grid_year_total = 0.0
            try:
                self._derived_grid_month_id = entry.options.get(OPT_KEY_DERIVED_GRID_MONTH_ID) or None
            except Exception:
                self._derived_grid_month_id = None
            try:
                self._derived_grid_year_id = entry.options.get(OPT_KEY_DERIVED_GRID_YEAR_ID) or None
            except Exception:
                self._derived_grid_year_id = None

            try:
                if entry.options.get(OPT_KEY_DERIVED_SOLAR_DAILY_LAST_VALUE) is not None:
                    self._derived_solar_daily_last_value = float(entry.options.get(OPT_KEY_DERIVED_SOLAR_DAILY_LAST_VALUE))
            except Exception:
                self._derived_solar_daily_last_value = None
            try:
                self._derived_solar_daily_last_date = entry.options.get(OPT_KEY_DERIVED_SOLAR_DAILY_LAST_DATE) or None
            except Exception:
                self._derived_solar_daily_last_date = None
            try:
                if entry.options.get(OPT_KEY_DERIVED_SOLAR_MONTH_TOTAL) is not None:
                    self._derived_solar_month_total = float(entry.options.get(OPT_KEY_DERIVED_SOLAR_MONTH_TOTAL))
            except Exception:
                self._derived_solar_month_total = 0.0
            try:
                if entry.options.get(OPT_KEY_DERIVED_SOLAR_YEAR_TOTAL) is not None:
                    self._derived_solar_year_total = float(entry.options.get(OPT_KEY_DERIVED_SOLAR_YEAR_TOTAL))
            except Exception:
                self._derived_solar_year_total = 0.0
            try:
                self._derived_solar_month_id = entry.options.get(OPT_KEY_DERIVED_SOLAR_MONTH_ID) or None
            except Exception:
                self._derived_solar_month_id = None
            try:
                self._derived_solar_year_id = entry.options.get(OPT_KEY_DERIVED_SOLAR_YEAR_ID) or None
            except Exception:
                self._derived_solar_year_id = None

            # Cost accumulation persisted values (best effort)
            try:
                if entry.options.get(OPT_KEY_COST_DAILY_LAST_GRID_KWH) is not None:
                    self._cost_daily_last_grid_kwh = float(entry.options.get(OPT_KEY_COST_DAILY_LAST_GRID_KWH))
            except Exception:
                self._cost_daily_last_grid_kwh = None
            try:
                if entry.options.get(OPT_KEY_COST_DAILY_LAST_SOLAR_KWH) is not None:
                    self._cost_daily_last_solar_kwh = float(entry.options.get(OPT_KEY_COST_DAILY_LAST_SOLAR_KWH))
            except Exception:
                self._cost_daily_last_solar_kwh = None
            try:
                self._cost_daily_date = entry.options.get(OPT_KEY_COST_DAILY_DATE) or None
            except Exception:
                self._cost_daily_date = None
            try:
                if entry.options.get(OPT_KEY_COST_DAILY_ACCUM) is not None:
                    self._cost_daily_accum = float(entry.options.get(OPT_KEY_COST_DAILY_ACCUM))
            except Exception:
                self._cost_daily_accum = 0.0
            try:
                if entry.options.get(OPT_KEY_COST_DAILY_FEED_IN_LOSS_ACCUM) is not None:
                    self._cost_daily_feed_in_loss_accum = float(entry.options.get(OPT_KEY_COST_DAILY_FEED_IN_LOSS_ACCUM))
            except Exception:
                self._cost_daily_feed_in_loss_accum = 0.0
            try:
                if entry.options.get(OPT_KEY_COST_DAILY_PV_CREDIT_ACCUM) is not None:
                    self._cost_daily_pv_credit_accum = float(entry.options.get(OPT_KEY_COST_DAILY_PV_CREDIT_ACCUM))
            except Exception:
                self._cost_daily_pv_credit_accum = 0.0

            # Derived cost aggregation (best effort)
            try:
                if entry.options.get(OPT_KEY_DERIVED_COST_DAILY_LAST_VALUE) is not None:
                    self._derived_cost_daily_last_value = float(entry.options.get(OPT_KEY_DERIVED_COST_DAILY_LAST_VALUE))
            except Exception:
                self._derived_cost_daily_last_value = None
            try:
                self._derived_cost_daily_last_date = entry.options.get(OPT_KEY_DERIVED_COST_DAILY_LAST_DATE) or None
            except Exception:
                self._derived_cost_daily_last_date = None
            try:
                if entry.options.get(OPT_KEY_DERIVED_COST_MONTH_TOTAL) is not None:
                    self._derived_cost_month_total = float(entry.options.get(OPT_KEY_DERIVED_COST_MONTH_TOTAL))
            except Exception:
                self._derived_cost_month_total = 0.0
            try:
                if entry.options.get(OPT_KEY_DERIVED_COST_YEAR_TOTAL) is not None:
                    self._derived_cost_year_total = float(entry.options.get(OPT_KEY_DERIVED_COST_YEAR_TOTAL))
            except Exception:
                self._derived_cost_year_total = 0.0
            try:
                self._derived_cost_month_id = entry.options.get(OPT_KEY_DERIVED_COST_MONTH_ID) or None
            except Exception:
                self._derived_cost_month_id = None
            try:
                self._derived_cost_year_id = entry.options.get(OPT_KEY_DERIVED_COST_YEAR_ID) or None
            except Exception:
                self._derived_cost_year_id = None

            try:
                if entry.options.get(OPT_KEY_DERIVED_COST_NET_DAILY_LAST_VALUE) is not None:
                    self._derived_cost_net_daily_last_value = float(entry.options.get(OPT_KEY_DERIVED_COST_NET_DAILY_LAST_VALUE))
            except Exception:
                self._derived_cost_net_daily_last_value = None
            try:
                self._derived_cost_net_daily_last_date = entry.options.get(OPT_KEY_DERIVED_COST_NET_DAILY_LAST_DATE) or None
            except Exception:
                self._derived_cost_net_daily_last_date = None
            try:
                if entry.options.get(OPT_KEY_DERIVED_COST_NET_MONTH_TOTAL) is not None:
                    self._derived_cost_net_month_total = float(entry.options.get(OPT_KEY_DERIVED_COST_NET_MONTH_TOTAL))
            except Exception:
                self._derived_cost_net_month_total = 0.0
            try:
                if entry.options.get(OPT_KEY_DERIVED_COST_NET_YEAR_TOTAL) is not None:
                    self._derived_cost_net_year_total = float(entry.options.get(OPT_KEY_DERIVED_COST_NET_YEAR_TOTAL))
            except Exception:
                self._derived_cost_net_year_total = 0.0
            try:
                self._derived_cost_net_month_id = entry.options.get(OPT_KEY_DERIVED_COST_NET_MONTH_ID) or None
            except Exception:
                self._derived_cost_net_month_id = None
            try:
                self._derived_cost_net_year_id = entry.options.get(OPT_KEY_DERIVED_COST_NET_YEAR_ID) or None
            except Exception:
                self._derived_cost_net_year_id = None
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

            # Run credit persisted values (best effort)
            try:
                if entry.options.get(OPT_KEY_FILTER_CREDIT_MINUTES) is not None:
                    self._filter_credit_minutes = float(entry.options.get(OPT_KEY_FILTER_CREDIT_MINUTES))
            except Exception:
                self._filter_credit_minutes = 0.0
            try:
                fc_exp = entry.options.get(OPT_KEY_FILTER_CREDIT_EXPIRES_AT)
                self._filter_credit_expires_at = dt_util.parse_datetime(fc_exp) if fc_exp else None
            except Exception:
                self._filter_credit_expires_at = None
            try:
                if entry.options.get(OPT_KEY_FROST_CREDIT_MINUTES) is not None:
                    self._frost_credit_minutes = float(entry.options.get(OPT_KEY_FROST_CREDIT_MINUTES))
            except Exception:
                self._frost_credit_minutes = 0.0
            try:
                fr_exp = entry.options.get(OPT_KEY_FROST_CREDIT_EXPIRES_AT)
                self._frost_credit_expires_at = dt_util.parse_datetime(fr_exp) if fr_exp else None
            except Exception:
                self._frost_credit_expires_at = None
            try:
                self._credit_streak_source = entry.options.get(OPT_KEY_CREDIT_STREAK_SOURCE) or None
            except Exception:
                self._credit_streak_source = None
            try:
                if entry.options.get(OPT_KEY_CREDIT_STREAK_MINUTES) is not None:
                    self._credit_streak_minutes = float(entry.options.get(OPT_KEY_CREDIT_STREAK_MINUTES))
            except Exception:
                self._credit_streak_minutes = 0.0

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
            self.away_active = False
            self.away_temp = DEFAULT_AWAY_TEMP
            self.heat_loss_w_per_c = DEFAULT_HEAT_LOSS_W_PER_C
            self.heat_startup_offset_minutes = DEFAULT_HEAT_STARTUP_OFFSET_MINUTES

            self._derived_grid_daily_last_value = None
            self._derived_grid_daily_last_date = None
            self._derived_grid_month_total = 0.0
            self._derived_grid_year_total = 0.0
            self._derived_grid_month_id = None
            self._derived_grid_year_id = None

            self._derived_solar_daily_last_value = None
            self._derived_solar_daily_last_date = None
            self._derived_solar_month_total = 0.0
            self._derived_solar_year_total = 0.0
            self._derived_solar_month_id = None
            self._derived_solar_year_id = None

            self._derived_energy_last_saved = None
            self._derived_energy_snapshot = None

            self._cost_daily_last_grid_kwh = None
            self._cost_daily_last_solar_kwh = None
            self._cost_daily_date = None
            self._cost_daily_accum = 0.0
            self._cost_daily_feed_in_loss_accum = 0.0
            self._cost_daily_pv_credit_accum = 0.0
            self._cost_persist_last_saved = None
            self._cost_persist_snapshot = None
            self._cost_last_tick_at = None
            self._cost_net_daily_last_value = None
            self._cost_net_daily_date = None

            self._derived_cost_daily_last_value = None
            self._derived_cost_daily_last_date = None
            self._derived_cost_month_total = 0.0
            self._derived_cost_year_total = 0.0
            self._derived_cost_month_id = None
            self._derived_cost_year_id = None

            self._derived_cost_net_daily_last_value = None
            self._derived_cost_net_daily_last_date = None
            self._derived_cost_net_month_total = 0.0
            self._derived_cost_net_year_total = 0.0
            self._derived_cost_net_month_id = None
            self._derived_cost_net_year_id = None
            self._derived_cost_last_saved = None
            self._derived_cost_snapshot = None

    def _update_derived_energy_from_daily(self, prefix: str, daily_value: float | None, now: datetime) -> tuple[float | None, float | None, bool]:
        """Return (month_total, year_total, changed) derived from a daily-reset sensor."""
        if daily_value is None:
            return None, None, False

        today = dt_util.as_local(now).date()
        month_id = today.strftime("%Y-%m")
        year_id = today.strftime("%Y")

        last_date = getattr(self, f"_derived_{prefix}_daily_last_date", None)
        last_value = getattr(self, f"_derived_{prefix}_daily_last_value", None)
        month_total = float(getattr(self, f"_derived_{prefix}_month_total", 0.0) or 0.0)
        year_total = float(getattr(self, f"_derived_{prefix}_year_total", 0.0) or 0.0)
        stored_month_id = getattr(self, f"_derived_{prefix}_month_id", None)
        stored_year_id = getattr(self, f"_derived_{prefix}_year_id", None)

        changed = False

        if stored_month_id != month_id:
            month_total = 0.0
            stored_month_id = month_id
            changed = True
        if stored_year_id != year_id:
            year_total = 0.0
            stored_year_id = year_id
            changed = True

        if last_date is None:
            last_date = today
            last_value = float(daily_value)
            changed = True
        else:
            # Convert stored date string to date if needed
            if isinstance(last_date, str):
                try:
                    last_date = datetime.strptime(last_date, "%Y-%m-%d").date()
                except Exception:
                    last_date = today
            if last_date != today:
                try:
                    if last_value is not None:
                        month_total += float(last_value)
                        year_total += float(last_value)
                except Exception:
                    pass
                last_date = today
                last_value = float(daily_value)
                changed = True
            else:
                try:
                    if last_value is None or float(last_value) != float(daily_value):
                        last_value = float(daily_value)
                        changed = True
                except Exception:
                    pass

        # Include current day partial value in derived totals
        try:
            derived_month = float(month_total) + float(daily_value)
        except Exception:
            derived_month = None
        try:
            derived_year = float(year_total) + float(daily_value)
        except Exception:
            derived_year = None

        setattr(self, f"_derived_{prefix}_daily_last_value", last_value)
        setattr(self, f"_derived_{prefix}_daily_last_date", last_date.strftime("%Y-%m-%d") if hasattr(last_date, "strftime") else last_date)
        setattr(self, f"_derived_{prefix}_month_total", month_total)
        setattr(self, f"_derived_{prefix}_year_total", year_total)
        setattr(self, f"_derived_{prefix}_month_id", stored_month_id)
        setattr(self, f"_derived_{prefix}_year_id", stored_year_id)

        return derived_month, derived_year, changed

    async def _maybe_persist_derived_energy_state(self, now: datetime) -> None:
        if not self.entry or self.entry.options is None:
            return

        snapshot = (
            self._derived_grid_daily_last_value,
            self._derived_grid_daily_last_date,
            self._derived_grid_month_total,
            self._derived_grid_year_total,
            self._derived_grid_month_id,
            self._derived_grid_year_id,
            self._derived_solar_daily_last_value,
            self._derived_solar_daily_last_date,
            self._derived_solar_month_total,
            self._derived_solar_year_total,
            self._derived_solar_month_id,
            self._derived_solar_year_id,
        )
        if self._derived_energy_snapshot == snapshot:
            return

        try:
            last_saved = self._derived_energy_last_saved
            if last_saved and (now - last_saved).total_seconds() < 30:
                return
        except Exception:
            pass

        opts = {**self.entry.options}
        opts[OPT_KEY_DERIVED_GRID_DAILY_LAST_VALUE] = self._derived_grid_daily_last_value
        opts[OPT_KEY_DERIVED_GRID_DAILY_LAST_DATE] = self._derived_grid_daily_last_date
        opts[OPT_KEY_DERIVED_GRID_MONTH_TOTAL] = self._derived_grid_month_total
        opts[OPT_KEY_DERIVED_GRID_YEAR_TOTAL] = self._derived_grid_year_total
        opts[OPT_KEY_DERIVED_GRID_MONTH_ID] = self._derived_grid_month_id
        opts[OPT_KEY_DERIVED_GRID_YEAR_ID] = self._derived_grid_year_id

        opts[OPT_KEY_DERIVED_SOLAR_DAILY_LAST_VALUE] = self._derived_solar_daily_last_value
        opts[OPT_KEY_DERIVED_SOLAR_DAILY_LAST_DATE] = self._derived_solar_daily_last_date
        opts[OPT_KEY_DERIVED_SOLAR_MONTH_TOTAL] = self._derived_solar_month_total
        opts[OPT_KEY_DERIVED_SOLAR_YEAR_TOTAL] = self._derived_solar_year_total
        opts[OPT_KEY_DERIVED_SOLAR_MONTH_ID] = self._derived_solar_month_id
        opts[OPT_KEY_DERIVED_SOLAR_YEAR_ID] = self._derived_solar_year_id

        await self._async_update_entry_options(opts)
        self._derived_energy_last_saved = now
        self._derived_energy_snapshot = snapshot

    async def _maybe_persist_cost_daily_state(self, now: datetime) -> None:
        if not self.entry or self.entry.options is None:
            return

        snapshot = (
            self._cost_daily_last_grid_kwh,
            self._cost_daily_last_solar_kwh,
            self._cost_daily_date,
            self._cost_daily_accum,
            self._cost_daily_feed_in_loss_accum,
            self._cost_daily_pv_credit_accum,
        )
        if self._cost_persist_snapshot == snapshot:
            return

        try:
            last_saved = self._cost_persist_last_saved
            if last_saved and (now - last_saved).total_seconds() < 30:
                return
        except Exception:
            pass

        opts = {**self.entry.options}
        opts[OPT_KEY_COST_DAILY_LAST_GRID_KWH] = self._cost_daily_last_grid_kwh
        opts[OPT_KEY_COST_DAILY_LAST_SOLAR_KWH] = self._cost_daily_last_solar_kwh
        opts[OPT_KEY_COST_DAILY_DATE] = self._cost_daily_date
        opts[OPT_KEY_COST_DAILY_ACCUM] = self._cost_daily_accum
        opts[OPT_KEY_COST_DAILY_FEED_IN_LOSS_ACCUM] = self._cost_daily_feed_in_loss_accum
        opts[OPT_KEY_COST_DAILY_PV_CREDIT_ACCUM] = self._cost_daily_pv_credit_accum

        await self._async_update_entry_options(opts)
        self._cost_persist_last_saved = now
        self._cost_persist_snapshot = snapshot

    async def _maybe_persist_derived_cost_state(self, now: datetime) -> None:
        if not self.entry or self.entry.options is None:
            return

        snapshot = (
            self._derived_cost_daily_last_value,
            self._derived_cost_daily_last_date,
            self._derived_cost_month_total,
            self._derived_cost_year_total,
            self._derived_cost_month_id,
            self._derived_cost_year_id,
            self._derived_cost_net_daily_last_value,
            self._derived_cost_net_daily_last_date,
            self._derived_cost_net_month_total,
            self._derived_cost_net_year_total,
            self._derived_cost_net_month_id,
            self._derived_cost_net_year_id,
        )
        if getattr(self, "_derived_cost_snapshot", None) == snapshot:
            return

        try:
            last_saved = getattr(self, "_derived_cost_last_saved", None)
            if last_saved and (now - last_saved).total_seconds() < 5 * 60:
                return
        except Exception:
            pass

        opts = {**self.entry.options}
        opts[OPT_KEY_DERIVED_COST_DAILY_LAST_VALUE] = self._derived_cost_daily_last_value
        opts[OPT_KEY_DERIVED_COST_DAILY_LAST_DATE] = self._derived_cost_daily_last_date
        opts[OPT_KEY_DERIVED_COST_MONTH_TOTAL] = self._derived_cost_month_total
        opts[OPT_KEY_DERIVED_COST_YEAR_TOTAL] = self._derived_cost_year_total
        opts[OPT_KEY_DERIVED_COST_MONTH_ID] = self._derived_cost_month_id
        opts[OPT_KEY_DERIVED_COST_YEAR_ID] = self._derived_cost_year_id

        opts[OPT_KEY_DERIVED_COST_NET_DAILY_LAST_VALUE] = self._derived_cost_net_daily_last_value
        opts[OPT_KEY_DERIVED_COST_NET_DAILY_LAST_DATE] = self._derived_cost_net_daily_last_date
        opts[OPT_KEY_DERIVED_COST_NET_MONTH_TOTAL] = self._derived_cost_net_month_total
        opts[OPT_KEY_DERIVED_COST_NET_YEAR_TOTAL] = self._derived_cost_net_year_total
        opts[OPT_KEY_DERIVED_COST_NET_MONTH_ID] = self._derived_cost_net_month_id
        opts[OPT_KEY_DERIVED_COST_NET_YEAR_ID] = self._derived_cost_net_year_id

        await self._async_update_entry_options(opts)
        setattr(self, "_derived_cost_last_saved", now)
        setattr(self, "_derived_cost_snapshot", snapshot)

    def _effective_heating_power(self, conf: dict, water_temp: float | None, outdoor_temp: float | None) -> float:
        """Return effective heating power in W after subtracting estimated heat loss."""
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

        # Subtract estimated heat loss (W) based on ΔT to outdoor temperature.
        loss_w = 0.0
        try:
            if water_temp is not None and outdoor_temp is not None:
                delta = max(0.0, float(water_temp) - float(outdoor_temp))
                loss_w = max(0.0, float(self.heat_loss_w_per_c or 0.0) * float(delta))
        except Exception:
            loss_w = 0.0
        effective = max(1.0, float(power_w) - float(loss_w))
        return effective

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

        power_w = self._effective_heating_power(conf, water_temp, self._get_float(conf.get(CONF_TEMP_OUTDOOR)))

        if not vol_l or vol_l <= 0 or power_w <= 0:
            return None

        # t_min in Minuten: V * 1.16 * deltaT / P * 60
        t_min = (vol_l * 1.16 * delta_t) / float(power_w) * 60.0
        try:
            base = max(0, int(round(t_min)))
            offset = float(self.heat_startup_offset_minutes or 0.0)
            return max(0, int(round(base + offset)))
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

    async def set_away(self, active: bool):
        """Aktiviert/deaktiviert Away-Modus und persistiert den Zustand."""
        active = bool(active)
        if active == bool(getattr(self, "away_active", False)):
            return

        self.away_active = active
        merged = {**(self.entry.data or {}), **(self.entry.options or {})}
        try:
            away_temp = float(merged.get(CONF_AWAY_TEMP, DEFAULT_AWAY_TEMP))
        except Exception:
            away_temp = DEFAULT_AWAY_TEMP
        try:
            min_t = float(merged.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))
        except Exception:
            min_t = DEFAULT_MIN_TEMP
        try:
            max_t = float(merged.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP))
        except Exception:
            max_t = DEFAULT_MAX_TEMP
        away_temp = max(min_t, min(max_t, away_temp))

        try:
            new_opts = {**self.entry.options}

            if active:
                # Ensure maintenance is off so filter/frost can run.
                self.maintenance_active = False
                new_opts.pop(OPT_KEY_MAINTENANCE_ACTIVE, None)

                # Store previous target temp for restore.
                if self.target_temp is not None:
                    new_opts[OPT_KEY_AWAY_PREV_TARGET] = float(self.target_temp)

                # Stop non-filter manual timers and pause to keep filtering active.
                if self.manual_timer_type in ("bathing", "chlorine"):
                    self.manual_timer_until = None
                    self.manual_timer_type = None
                    self.manual_timer_duration = None
                    new_opts.pop(OPT_KEY_MANUAL_UNTIL, None)
                    new_opts.pop(OPT_KEY_MANUAL_TYPE, None)
                    new_opts.pop(OPT_KEY_MANUAL_DURATION, None)
                if self.pause_until is not None:
                    self.pause_until = None
                    self.pause_duration = None
                    new_opts.pop(OPT_KEY_PAUSE_UNTIL, None)
                    new_opts.pop(OPT_KEY_PAUSE_DURATION, None)

                # Apply away target temperature.
                self.target_temp = away_temp
                new_opts[OPT_KEY_TARGET_TEMP] = float(self.target_temp)
                new_opts[OPT_KEY_AWAY_ACTIVE] = True
            else:
                new_opts.pop(OPT_KEY_AWAY_ACTIVE, None)
                prev_target = new_opts.pop(OPT_KEY_AWAY_PREV_TARGET, None)
                if prev_target is not None:
                    try:
                        self.target_temp = float(prev_target)
                        new_opts[OPT_KEY_TARGET_TEMP] = float(self.target_temp)
                    except Exception:
                        pass

            await self._async_update_entry_options(new_opts)
        except Exception:
            _LOGGER.exception("Fehler beim Speichern von Away-Modus")

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
        # Preserve sticky config keys (calendar/weather guard) when updating options.
        try:
            merged = {**(self.entry.data or {}), **(self.entry.options or {})}
            for key in (
                CONF_ENABLE_EVENT_WEATHER_GUARD,
                CONF_EVENT_WEATHER_ENTITY,
                CONF_EVENT_RAIN_PROBABILITY,
                CONF_POOL_CALENDAR,
                CONF_HOLIDAY_CALENDAR,
                CONF_QUIET_START,
                CONF_QUIET_END,
                CONF_QUIET_START_WEEKEND,
                CONF_QUIET_END_WEEKEND,
            ):
                if key in merged and key not in options:
                    options[key] = merged.get(key)
        except Exception:
            pass
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

    def _normalize_credit_sources(self, raw) -> list[str]:
        if raw is None:
            return list(DEFAULT_CREDIT_SOURCES)
        if isinstance(raw, (list, tuple, set)):
            return [str(x).strip().lower() for x in raw if str(x).strip()]
        if isinstance(raw, str):
            return [s.strip().lower() for s in raw.split(",") if s.strip()]
        return list(DEFAULT_CREDIT_SOURCES)

    def _credit_source_from_reasons(self, run_reason: str | None, heat_reason: str | None) -> str | None:
        rr = (run_reason or "").strip().lower()
        hr = (heat_reason or "").strip().lower()
        if rr in ("bathing", "filter", "chlorine", "frost", "preheat", "pv"):
            return rr
        if hr in ("bathing", "filter", "chlorine", "preheat", "pv", "thermostat"):
            return hr
        return None

    def _flush_credit_streak(
        self,
        now: datetime,
        min_credit: float,
        credit_sources: list[str],
        filter_interval: int | None,
        frost_interval: int | None,
        frost_run_mins: int | None,
        frost_danger: bool,
        frost_is_severe: bool,
    ) -> None:
        if not self._credit_streak_source or self._credit_streak_minutes <= 0:
            return
        if self._credit_streak_source not in credit_sources:
            self._credit_streak_minutes = 0.0
            self._credit_streak_source = None
            return
        if self._credit_streak_minutes < float(min_credit or 0):
            return

        minutes = float(self._credit_streak_minutes)
        self._last_credit_source = self._credit_streak_source
        self._last_credit_minutes = minutes

        # Filter credit window
        if filter_interval and getattr(self, "filter_minutes", None):
            if (self._filter_credit_expires_at is None) or (now > self._filter_credit_expires_at):
                self._filter_credit_minutes = 0.0
                self._filter_credit_expires_at = now + timedelta(minutes=int(filter_interval))
            self._filter_credit_minutes = min(float(self.filter_minutes), float(self._filter_credit_minutes) + minutes)

        # Frost credit window (only for mild frost)
        if frost_danger and (not frost_is_severe) and frost_interval and frost_run_mins:
            if (self._frost_credit_expires_at is None) or (now > self._frost_credit_expires_at):
                self._frost_credit_minutes = 0.0
                self._frost_credit_expires_at = now + timedelta(minutes=int(frost_interval))
            cap = max(float(frost_interval), float(frost_run_mins))
            self._frost_credit_minutes = min(cap, float(self._frost_credit_minutes) + minutes)

        # Reset streak after flushing
        self._credit_streak_minutes = 0.0
        self._credit_streak_source = None

    def _update_run_credit(
        self,
        now: datetime,
        min_credit: float,
        credit_sources: list[str],
        filter_interval: int | None,
        frost_interval: int | None,
        frost_run_mins: int | None,
        frost_danger: bool,
        frost_is_severe: bool,
    ) -> None:
        last_ts = self._credit_last_update or now
        try:
            dt_min = max(0.0, (now - last_ts).total_seconds() / 60.0)
        except Exception:
            dt_min = 0.0
        self._credit_last_update = now

        if dt_min <= 0:
            return

        # Use previous cycle's run source/activity to credit elapsed time
        if self._last_run_active and self._last_run_source in credit_sources:
            if self._credit_streak_source and self._credit_streak_source != self._last_run_source:
                self._flush_credit_streak(
                    now,
                    min_credit,
                    credit_sources,
                    filter_interval,
                    frost_interval,
                    frost_run_mins,
                    frost_danger,
                    frost_is_severe,
                )
            self._credit_streak_source = self._last_run_source
            self._credit_streak_minutes = float(self._credit_streak_minutes or 0.0) + float(dt_min)
        else:
            # Run ended or source not eligible: flush any streak
            self._flush_credit_streak(
                now,
                min_credit,
                credit_sources,
                filter_interval,
                frost_interval,
                frost_run_mins,
                frost_danger,
                frost_is_severe,
            )

    async def _maybe_persist_credit_state(self, now: datetime) -> None:
        if not self.entry or self.entry.options is None:
            return

        filter_minutes = float(self._filter_credit_minutes or 0.0)
        frost_minutes = float(self._frost_credit_minutes or 0.0)
        streak_minutes = float(self._credit_streak_minutes or 0.0)
        filter_exp = self._filter_credit_expires_at.isoformat() if self._filter_credit_expires_at else None
        frost_exp = self._frost_credit_expires_at.isoformat() if self._frost_credit_expires_at else None
        streak_source = self._credit_streak_source or None

        snapshot = (filter_minutes, filter_exp, frost_minutes, frost_exp, streak_source, streak_minutes)
        if self._credit_persist_snapshot == snapshot:
            return

        # Throttle saves to reduce churn.
        try:
            last_saved = self._credit_persist_last_saved
            if last_saved and (now - last_saved).total_seconds() < 5 * 60:
                return
        except Exception:
            pass

        opts = {**self.entry.options}
        opts[OPT_KEY_FILTER_CREDIT_MINUTES] = filter_minutes
        opts[OPT_KEY_FROST_CREDIT_MINUTES] = frost_minutes
        opts[OPT_KEY_CREDIT_STREAK_MINUTES] = streak_minutes
        if streak_source:
            opts[OPT_KEY_CREDIT_STREAK_SOURCE] = streak_source
        else:
            opts.pop(OPT_KEY_CREDIT_STREAK_SOURCE, None)
        if filter_exp:
            opts[OPT_KEY_FILTER_CREDIT_EXPIRES_AT] = filter_exp
        else:
            opts.pop(OPT_KEY_FILTER_CREDIT_EXPIRES_AT, None)
        if frost_exp:
            opts[OPT_KEY_FROST_CREDIT_EXPIRES_AT] = frost_exp
        else:
            opts.pop(OPT_KEY_FROST_CREDIT_EXPIRES_AT, None)

        await self._async_update_entry_options(opts)
        self._credit_persist_last_saved = now
        self._credit_persist_snapshot = snapshot

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

            # Ensure aux_allowed is always a boolean (defensive)
            self.aux_allowed = bool(getattr(self, "aux_allowed", getattr(self, "aux_enabled", False)))
            # Keep legacy alias in sync
            self.aux_enabled = self.aux_allowed

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
            # Away mode flag (reduced activity)
            self.away_active = bool(conf.get(OPT_KEY_AWAY_ACTIVE, False))

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

            # Electricity price (fixed or dynamic entity)
            electricity_price = None
            price_entity = conf.get(CONF_ELECTRICITY_PRICE_ENTITY)
            price_from_entity = self._get_float(price_entity) if price_entity else None
            if price_from_entity is not None:
                electricity_price = price_from_entity
            else:
                try:
                    raw_price = conf.get(CONF_ELECTRICITY_PRICE) if CONF_ELECTRICITY_PRICE in conf else None
                    electricity_price = float(raw_price) if raw_price is not None else None
                except Exception:
                    electricity_price = None

            # Feed-in tariff (fixed or dynamic entity)
            feed_in_tariff = None
            feed_in_entity = conf.get(CONF_FEED_IN_TARIFF_ENTITY)
            feed_in_from_entity = self._get_float(feed_in_entity) if feed_in_entity else None
            if feed_in_from_entity is not None:
                feed_in_tariff = feed_in_from_entity
            else:
                try:
                    raw_tariff = conf.get(CONF_FEED_IN_TARIFF) if CONF_FEED_IN_TARIFF in conf else None
                    feed_in_tariff = float(raw_tariff) if raw_tariff is not None else None
                except Exception:
                    feed_in_tariff = None

            # Pool-only energy sensors (kWh)
            pool_energy_kwh_base = self._get_float(conf.get(CONF_POOL_ENERGY_ENTITY_BASE))
            pool_energy_kwh_aux = self._get_float(conf.get(CONF_POOL_ENERGY_ENTITY_AUX))
            if pool_energy_kwh_base is not None or pool_energy_kwh_aux is not None:
                pool_energy_kwh = float(pool_energy_kwh_base or 0.0) + float(pool_energy_kwh_aux or 0.0)
            else:
                pool_energy_kwh = self._get_float(conf.get(CONF_POOL_ENERGY_ENTITY))

            pool_energy_kwh_daily_base = self._get_float(conf.get(CONF_POOL_ENERGY_ENTITY_BASE_DAILY))
            pool_energy_kwh_daily_aux = self._get_float(conf.get(CONF_POOL_ENERGY_ENTITY_AUX_DAILY))
            if pool_energy_kwh_daily_base is not None or pool_energy_kwh_daily_aux is not None:
                pool_energy_kwh_daily = float(pool_energy_kwh_daily_base or 0.0) + float(pool_energy_kwh_daily_aux or 0.0)
            else:
                pool_energy_kwh_daily = self._get_float(conf.get(CONF_POOL_ENERGY_ENTITY_DAILY))

            # Optional pool solar energy (daily) to compute net costs
            pool_solar_kwh_daily = self._get_float(conf.get(CONF_SOLAR_ENERGY_ENTITY_DAILY))

            # Use pool energy as the basis for cost calculations
            load_kwh = pool_energy_kwh
            load_kwh_daily = pool_energy_kwh_daily
            net_load_kwh_daily = load_kwh_daily
            if (load_kwh_daily is not None) and (pool_solar_kwh_daily is not None):
                try:
                    net_load_kwh_daily = max(0.0, float(load_kwh_daily) - float(pool_solar_kwh_daily))
                except Exception:
                    net_load_kwh_daily = load_kwh_daily
            load_kwh_monthly = None
            load_kwh_yearly = None

            # Effective PV surplus for pool usage (W):
            # - default: pv_surplus_sensor already reports surplus/export in W
            # - if pv_house_load_sensor is configured: treat pv_surplus_sensor as PV production in W
            #   and compute surplus as production - (house_load - pool_load)
            pv_power_raw = self._get_float(conf.get(CONF_PV_SURPLUS_SENSOR))
            pv_house_load_w = self._get_float(conf.get(CONF_PV_HOUSE_LOAD_SENSOR))
            total_pool_power_w = None
            if main_power is not None or aux_power is not None:
                total_pool_power_w = float(main_power or 0.0) + float(aux_power or 0.0)
            pv_surplus_for_pool_w = None
            if pv_power_raw is not None:
                try:
                    pv_input_w = float(pv_power_raw)
                    if pv_house_load_w is not None:
                        house_wo_pool_w = max(0.0, float(pv_house_load_w))
                        if total_pool_power_w is not None:
                            house_wo_pool_w = max(0.0, house_wo_pool_w - float(total_pool_power_w))
                        pv_surplus_for_pool_w = max(0.0, pv_input_w - house_wo_pool_w)
                    else:
                        pv_surplus_for_pool_w = max(0.0, pv_input_w)
                except Exception:
                    pv_surplus_for_pool_w = None

            # Derive month/year totals from daily sensors when not provided
            derived_changed = False
            if load_kwh_daily is not None and (load_kwh_monthly is None or load_kwh_yearly is None):
                d_month, d_year, changed = self._update_derived_energy_from_daily("grid", load_kwh_daily, now)
                derived_changed = derived_changed or changed
                if load_kwh_monthly is None:
                    load_kwh_monthly = d_month
                if load_kwh_yearly is None:
                    load_kwh_yearly = d_year

            # Persist derived aggregation state (best-effort, throttled)
            if derived_changed:
                try:
                    await self._maybe_persist_derived_energy_state(now)
                except Exception:
                    pass

            def _calc_energy_costs(load_kwh):
                cost = None
                try:
                    if load_kwh is not None and electricity_price is not None:
                        cost = float(load_kwh) * float(electricity_price)
                except Exception:
                    cost = None
                return cost

            energy_cost_daily = _calc_energy_costs(load_kwh_daily)
            energy_cost_monthly = _calc_energy_costs(load_kwh_monthly)
            energy_cost_yearly = _calc_energy_costs(load_kwh_yearly)
            energy_feed_in_loss_daily = None
            energy_feed_in_loss_monthly = None
            energy_feed_in_loss_yearly = None
            energy_cost_net_daily = _calc_energy_costs(net_load_kwh_daily)
            energy_cost_net_monthly = energy_cost_monthly
            energy_cost_net_yearly = energy_cost_yearly

            # Time-weighted cost accumulation (daily reset, monotonic within day)
            # Prefer daily kWh sensors if provided; otherwise fall back to total kWh sensors
            # and compute deltas within the current day.
            cost_daily_changed = False
            try:
                today = dt_util.as_local(now).date()
            except Exception:
                today = now.date()

            last_date = self._cost_daily_date
            if isinstance(last_date, str):
                try:
                    last_date = datetime.strptime(last_date, "%Y-%m-%d").date()
                except Exception:
                    last_date = None

            cost_kwh_value = load_kwh_daily if load_kwh_daily is not None else load_kwh

            if last_date != today:
                self._cost_daily_accum = 0.0
                self._cost_daily_feed_in_loss_accum = 0.0
                self._cost_daily_pv_credit_accum = 0.0
                self._cost_daily_date = today.strftime("%Y-%m-%d")
                self._cost_daily_last_grid_kwh = cost_kwh_value
                self._cost_last_tick_at = now
                cost_daily_changed = True

            if cost_kwh_value is not None and self._cost_daily_last_grid_kwh is None:
                self._cost_daily_last_grid_kwh = cost_kwh_value
                cost_daily_changed = True

            delta_grid = None
            if cost_kwh_value is not None and self._cost_daily_last_grid_kwh is not None:
                try:
                    delta_grid = float(cost_kwh_value) - float(self._cost_daily_last_grid_kwh)
                except Exception:
                    delta_grid = None
                if delta_grid is not None and delta_grid < 0:
                    # Sensor reset detected; reset baseline for the day
                    self._cost_daily_last_grid_kwh = cost_kwh_value
                    delta_grid = 0.0
                    cost_daily_changed = True

            if delta_grid is not None:
                if electricity_price is not None and delta_grid > 0:
                    self._cost_daily_accum = float(self._cost_daily_accum or 0.0) + float(delta_grid) * float(electricity_price)
                    cost_daily_changed = True
                self._cost_daily_last_grid_kwh = cost_kwh_value

            # Fallback PV credit/feed-in-loss integration from instantaneous power.
            # This is used when no dedicated daily solar kWh sensor is configured.
            try:
                last_tick = getattr(self, "_cost_last_tick_at", None)
                elapsed_h = 0.0
                if last_tick is not None:
                    elapsed_h = max(0.0, (now - last_tick).total_seconds() / 3600.0)
                self._cost_last_tick_at = now

                if elapsed_h > 0.0:
                    total_power_w_for_cost = None
                    if main_power is not None or aux_power is not None:
                        total_power_w_for_cost = float(main_power or 0.0) + float(aux_power or 0.0)

                    if total_power_w_for_cost is not None and total_power_w_for_cost > 0.0:
                        pv_surplus_w = max(0.0, float(pv_surplus_for_pool_w or 0.0))
                        overlap_w = min(float(total_power_w_for_cost), pv_surplus_w)

                        if overlap_w > 0.0:
                            if electricity_price is not None:
                                pv_credit_inc = (overlap_w / 1000.0) * float(electricity_price) * elapsed_h
                                if pv_credit_inc > 0.0:
                                    self._cost_daily_pv_credit_accum = float(self._cost_daily_pv_credit_accum or 0.0) + pv_credit_inc
                                    cost_daily_changed = True
                            if feed_in_tariff is not None:
                                feed_in_loss_inc = (overlap_w / 1000.0) * float(feed_in_tariff) * elapsed_h
                                if feed_in_loss_inc > 0.0:
                                    self._cost_daily_feed_in_loss_accum = float(self._cost_daily_feed_in_loss_accum or 0.0) + feed_in_loss_inc
                                    cost_daily_changed = True
            except Exception:
                pass

            if self._cost_daily_date is not None:
                try:
                    energy_cost_daily = float(self._cost_daily_accum or 0.0)
                    energy_feed_in_loss_daily = float(self._cost_daily_feed_in_loss_accum or 0.0)
                    # Net daily cost: prefer solar-adjusted net load if provided; otherwise fall back to gross+loss.
                    if pool_solar_kwh_daily is not None and electricity_price is not None:
                        try:
                            if net_load_kwh_daily is not None:
                                energy_cost_net_daily = float(max(0.0, float(net_load_kwh_daily))) * float(electricity_price)
                            else:
                                # Fallback when only total energy sensors are available:
                                # subtract daily solar kWh at current price from the gross daily cost.
                                energy_cost_net_daily = max(
                                    0.0,
                                    float(energy_cost_daily or 0.0) - float(pool_solar_kwh_daily) * float(electricity_price),
                                )
                        except Exception:
                            energy_cost_net_daily = float(energy_cost_daily or 0.0) + float(energy_feed_in_loss_daily or 0.0)
                    elif electricity_price is not None:
                        energy_cost_net_daily = max(
                            0.0,
                            float(energy_cost_daily or 0.0) - float(self._cost_daily_pv_credit_accum or 0.0),
                        )
                    else:
                        energy_cost_net_daily = float(energy_cost_daily or 0.0) + float(energy_feed_in_loss_daily or 0.0)
                except Exception:
                    pass

            # Net daily cost should not decrease within a day (avoid drops when PV offsets rise).
            try:
                today = dt_util.as_local(now).date()
                if getattr(self, "_cost_net_daily_date", None) != today:
                    self._cost_net_daily_date = today
                    self._cost_net_daily_last_value = None
                if energy_cost_net_daily is None:
                    if self._cost_net_daily_last_value is not None:
                        energy_cost_net_daily = float(self._cost_net_daily_last_value)
                else:
                    current_net = float(energy_cost_net_daily)
                    if self._cost_net_daily_last_value is None or current_net >= float(self._cost_net_daily_last_value):
                        self._cost_net_daily_last_value = current_net
                    else:
                        energy_cost_net_daily = float(self._cost_net_daily_last_value)
            except Exception:
                pass

            if cost_daily_changed:
                try:
                    await self._maybe_persist_cost_daily_state(now)
                except Exception:
                    pass

            # Derive month/year costs from daily accumulated costs (monotonic, tariff-weighted)
            derived_cost_changed = False
            if energy_cost_daily is not None:
                d_month, d_year, changed = self._update_derived_energy_from_daily("cost", energy_cost_daily, now)
                derived_cost_changed = derived_cost_changed or changed
                if d_month is not None:
                    energy_cost_monthly = d_month
                if d_year is not None:
                    energy_cost_yearly = d_year

            if energy_cost_net_daily is not None:
                d_month, d_year, changed = self._update_derived_energy_from_daily("cost_net", energy_cost_net_daily, now)
                derived_cost_changed = derived_cost_changed or changed
                if d_month is not None:
                    energy_cost_net_monthly = d_month
                if d_year is not None:
                    energy_cost_net_yearly = d_year

            if derived_cost_changed:
                try:
                    await self._maybe_persist_derived_cost_state(now)
                except Exception:
                    pass

            # Total power and current cost per hour (best effort)
            total_power_w = None
            if main_power is not None or aux_power is not None:
                total_power_w = float(main_power or 0.0) + float(aux_power or 0.0)
            power_cost_per_hour = None
            try:
                if total_power_w is not None and electricity_price is not None:
                    power_cost_per_hour = (float(total_power_w) / 1000.0) * float(electricity_price)
            except Exception:
                power_cost_per_hour = None
            
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

            # Run credit / merge optimization options
            try:
                merge_window_minutes = int(conf.get(CONF_MERGE_WINDOW_MINUTES, DEFAULT_MERGE_WINDOW_MINUTES))
            except Exception:
                merge_window_minutes = DEFAULT_MERGE_WINDOW_MINUTES
            try:
                min_gap_minutes = int(conf.get(CONF_MIN_GAP_MINUTES, DEFAULT_MIN_GAP_MINUTES))
            except Exception:
                min_gap_minutes = DEFAULT_MIN_GAP_MINUTES
            try:
                max_merge_run_minutes = int(conf.get(CONF_MAX_MERGE_RUN_MINUTES, DEFAULT_MAX_MERGE_RUN_MINUTES))
            except Exception:
                max_merge_run_minutes = DEFAULT_MAX_MERGE_RUN_MINUTES
            try:
                min_credit_minutes = float(conf.get(CONF_MIN_CREDIT_MINUTES, DEFAULT_MIN_CREDIT_MINUTES))
            except Exception:
                min_credit_minutes = DEFAULT_MIN_CREDIT_MINUTES
            credit_sources = self._normalize_credit_sources(conf.get(CONF_CREDIT_SOURCES, DEFAULT_CREDIT_SOURCES))

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
            frost_credit_shift = 0
            interval = max(1, frost_mild_interval)
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
                # Apply credit shift (mild frost only): shift the cycle later
                frost_credit_effective = float(self._frost_credit_minutes or 0.0)
                if self._credit_streak_source in credit_sources and float(self._credit_streak_minutes or 0.0) >= float(min_credit_minutes or 0):
                    frost_credit_effective += float(self._credit_streak_minutes or 0.0)
                frost_credit_shift = 0
                if frost_danger and (not frost_is_severe) and interval > 0:
                    frost_credit_shift = int(min(float(interval - 1), max(0.0, frost_credit_effective))) if interval > 1 else 0
                epoch_minutes_eff = epoch_minutes - frost_credit_shift
                frost_active = (run_mins > 0) and ((epoch_minutes_eff % interval) < run_mins)

            # Update credit based on previous run (affects frost/filter scheduling)
            self._update_run_credit(
                now=now,
                min_credit=min_credit_minutes,
                credit_sources=credit_sources,
                filter_interval=getattr(self, "filter_interval", DEFAULT_FILTER_INTERVAL),
                frost_interval=interval if frost_danger else None,
                frost_run_mins=frost_run_mins if frost_danger else None,
                frost_danger=frost_danger,
                frost_is_severe=frost_is_severe,
            )

            # Persist run credit state (best effort, throttled)
            try:
                await self._maybe_persist_credit_state(now)
            except Exception:
                pass

            # Frost-Timer: Wenn frost_active, berechne Restlaufzeit und setze Timer-Attribute
            frost_timer_mins = None
            frost_timer_active = False
            frost_timer_duration = None
            frost_timer_type = None
            if frost_active and frost_danger and frost_run_mins > 0:
                now_local = dt_util.as_local(now)
                epoch_minutes = int(now_local.timestamp() // 60)
                epoch_minutes_eff = epoch_minutes - (frost_credit_shift if frost_danger and (not frost_is_severe) else 0)
                rem = frost_run_mins - (epoch_minutes_eff % max(1, interval))
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
            power_w = self._effective_heating_power(conf, water_temp, outdoor_temp)

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
                    base = max(0, int(round(t_min)))
                    offset = float(self.heat_startup_offset_minutes or 0.0)
                    heat_time = max(0, int(round(base + offset)))
                except Exception:
                    heat_time = None

            cal = await self._get_next_event(conf.get(CONF_POOL_CALENDAR))
            cal_next = (cal or {}).get("next") or {}
            cal_ongoing = (cal or {}).get("ongoing") or {}

            _LOGGER.debug(
                "Calendar snapshot (%s) next=%s ongoing=%s",
                getattr(self.entry, "entry_id", None),
                {
                    "start": cal_next.get("start"),
                    "end": cal_next.get("end"),
                    "summary": cal_next.get("summary"),
                }
                if cal_next
                else None,
                {
                    "start": cal_ongoing.get("start"),
                    "end": cal_ongoing.get("end"),
                    "summary": cal_ongoing.get("summary"),
                }
                if cal_ongoing
                else None,
            )

            # Weather guard for calendar events (optional)
            enable_event_weather_guard = bool(conf.get(CONF_ENABLE_EVENT_WEATHER_GUARD, False))
            weather_entity = conf.get(CONF_EVENT_WEATHER_ENTITY)
            try:
                rain_threshold = int(conf.get(CONF_EVENT_RAIN_PROBABILITY, DEFAULT_EVENT_RAIN_PROBABILITY))
            except Exception:
                rain_threshold = DEFAULT_EVENT_RAIN_PROBABILITY

            event_rain_probability = None
            event_rain_blocked = False
            if enable_event_weather_guard and weather_entity and (cal_next.get("start") or cal_ongoing.get("start")):
                forecast = await self._get_hourly_forecast(weather_entity)
                if cal_next.get("start"):
                    prob, blocked = self._event_rain_check(cal_next.get("start"), cal_next.get("end"), forecast, rain_threshold)
                    if prob is not None:
                        event_rain_probability = prob
                    if blocked:
                        event_rain_blocked = True
                if cal_ongoing.get("start"):
                    prob_now, blocked_now = self._event_rain_check(cal_ongoing.get("start"), cal_ongoing.get("end"), forecast, rain_threshold)
                    if event_rain_probability is None and prob_now is not None:
                        event_rain_probability = prob_now
                    if blocked_now:
                        event_rain_blocked = True

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
            pv_raw = pv_surplus_for_pool_w
            pv_val = pv_raw if enable_pv else None

            # Net cost and feed-in loss (best effort). pv_raw is treated as surplus (exportable) power in W.
            power_cost_per_hour_net = None
            power_cost_feed_in_loss_per_hour = None
            try:
                if total_power_w is not None and electricity_price is not None:
                    pv_surplus_w = float(pv_raw) if pv_raw is not None else 0.0
                    pv_surplus_w = max(0.0, pv_surplus_w)
                    net_grid_w = max(0.0, float(total_power_w) - pv_surplus_w)
                    power_cost_per_hour_net = (net_grid_w / 1000.0) * float(electricity_price)

                if total_power_w is not None and feed_in_tariff is not None:
                    pv_surplus_w = float(pv_raw) if pv_raw is not None else 0.0
                    pv_surplus_w = max(0.0, pv_surplus_w)
                    feed_in_loss_w = min(float(total_power_w), pv_surplus_w)
                    power_cost_feed_in_loss_per_hour = (feed_in_loss_w / 1000.0) * float(feed_in_tariff)
            except Exception:
                power_cost_per_hour_net = None
                power_cost_feed_in_loss_per_hour = None

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

            # PV band sensors for chart coloring (low/mid/high based on thresholds + pv_allows hysteresis)
            pv_band_low = None
            pv_band_mid_on = None
            pv_band_mid_off = None
            pv_band_high = None
            try:
                pv_for_band = pv_raw if pv_raw is not None else pv_smoothed
                pv_num = float(pv_for_band) if pv_for_band is not None else None
            except Exception:
                pv_num = None
            if pv_num is not None:
                try:
                    if pv_num <= float(off_th):
                        pv_band_low = round(pv_num, 1)
                    elif pv_num >= float(on_th):
                        pv_band_high = round(pv_num, 1)
                    else:
                        if pv_allows:
                            pv_band_mid_on = round(pv_num, 1)
                        else:
                            pv_band_mid_off = round(pv_num, 1)
                except Exception:
                    pv_band_low = None
                    pv_band_mid_on = None
                    pv_band_mid_off = None
                    pv_band_high = None
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

            # Enforce minimum gap between runs (unless severe frost)
            min_gap_remaining = 0
            try:
                if self._last_run_end and min_gap_minutes and min_gap_minutes > 0:
                    min_gap_remaining = max(0, int(((self._last_run_end + timedelta(minutes=min_gap_minutes)) - now).total_seconds() / 60))
            except Exception:
                min_gap_remaining = 0

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
                        epoch_minutes_eff = epoch_minutes - (frost_credit_shift if frost_danger and (not frost_is_severe) else 0)
                        rem = epoch_minutes_eff % max(1, int(interval))
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

            # Minimum gap between runs (skip mild frost if we just ran recently)
            if frost_danger and (not frost_is_severe) and min_gap_remaining > 0:
                frost_active = False
                if next_frost_mins is None or next_frost_mins < min_gap_remaining:
                    next_frost_mins = min_gap_remaining

            # If there is no frost danger, do not expose a "next frost" countdown.
            if (not enable_frost) or (not frost_danger):
                next_frost_mins = None

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

            # Credit-aware merge: if next filter start is close to next frost run, shift filter to end at frost start
            try:
                if (
                    enable_auto_filter
                    and getattr(self, "next_filter_start", None)
                    and next_frost_mins is not None
                    and frost_danger
                    and (not frost_is_severe)
                ):
                    next_frost_dt = now + timedelta(minutes=int(max(0, next_frost_mins)))
                    delta_min = (next_frost_dt - self.next_filter_start).total_seconds() / 60.0
                    if delta_min >= 0 and delta_min <= max(0, int(merge_window_minutes)):
                        # Determine combined run length (cap by max_merge_run_minutes)
                        filter_credit_effective = float(self._filter_credit_minutes or 0.0)
                        if self._credit_streak_source in credit_sources and float(self._credit_streak_minutes or 0.0) >= float(min_credit_minutes or 0):
                            filter_credit_effective += float(self._credit_streak_minutes or 0.0)
                        filter_missing = max(0.0, float(getattr(self, "filter_minutes", DEFAULT_FILTER_DURATION)) - filter_credit_effective)
                        merge_run = max(float(filter_missing), float(frost_run_mins or 0))
                        if max_merge_run_minutes and max_merge_run_minutes > 0:
                            merge_run = min(float(max_merge_run_minutes), merge_run)
                        if merge_run > 0:
                            merged_start = next_frost_dt - timedelta(minutes=merge_run)
                            if merged_start > now and merged_start != self.next_filter_start:
                                self.next_filter_start = merged_start
                                try:
                                    new_opts = {**self.entry.options, OPT_KEY_FILTER_NEXT: merged_start.isoformat()}
                                    await self._async_update_entry_options(new_opts)
                                except Exception:
                                    _LOGGER.exception("Fehler beim Verschieben von next_filter_start (Merge-Frost)")
            except Exception:
                pass

            next_filter_mins = None
            if getattr(self, "next_filter_start", None):
                next_filter_mins = max(0, round((self.next_filter_start - now).total_seconds() / 60))

            # Effective credit (including current streak) for transparency and scheduling
            filter_credit_effective = float(self._filter_credit_minutes or 0.0)
            frost_credit_effective = float(self._frost_credit_minutes or 0.0)
            if self._credit_streak_source in credit_sources and float(self._credit_streak_minutes or 0.0) >= float(min_credit_minutes or 0):
                filter_credit_effective += float(self._credit_streak_minutes or 0.0)
                frost_credit_effective += float(self._credit_streak_minutes or 0.0)
            filter_missing_minutes = max(0, int(round(float(getattr(self, "filter_minutes", DEFAULT_FILTER_DURATION)) - filter_credit_effective)))

            # =========================
            # Adaptive heating tuning (loss + startup offset)
            # =========================
            try:
                if water_temp is not None:
                    # Update loss coefficient while pool is OFF (no pump, no aux heat)
                    if (not pump_switch_on) and (not aux_heating_switch_on):
                        if self._last_temp_ts is None or self._last_temp_value is None:
                            self._last_temp_ts = now
                            self._last_temp_value = float(water_temp)
                        else:
                            dt_min = max(0.0, (now - self._last_temp_ts).total_seconds() / 60.0)
                            # Use a longer window to handle sparse sensor updates (often 15–30 min).
                            # This avoids zero-delta samples from short intervals.
                            if dt_min >= 60:
                                if outdoor_temp is not None and vol_l:
                                    dtemp = float(water_temp) - float(self._last_temp_value)
                                    if dtemp < 0:
                                        cooling_rate = abs(dtemp) / dt_min  # °C/min
                                        delta = max(0.1, float(water_temp) - float(outdoor_temp))
                                        loss_w = float(vol_l) * 1.16 * float(cooling_rate) * 60.0
                                        est_w_per_c = max(0.0, loss_w / delta)
                                        # EMA smoothing
                                        alpha = 0.2
                                        self.heat_loss_w_per_c = max(0.0, (1 - alpha) * float(self.heat_loss_w_per_c) + alpha * est_w_per_c)
                                # refresh baseline after a full window
                                self._last_temp_ts = now
                                self._last_temp_value = float(water_temp)

                    # Update startup offset based on how long it takes to see first warming
                    # Use the physical aux heater switch state to avoid relying on heat_reason
                    # (which may not be initialized yet in this update cycle).
                    heat_active = bool(pump_switch_on and aux_heating_switch_on)
                    if heat_active and not self._last_heat_active:
                        self._heat_start_ts = now
                        self._heat_start_temp = float(water_temp)
                        self._heat_start_reached = False
                    if heat_active and (self._heat_start_ts is not None) and (not self._heat_start_reached):
                        try:
                            if float(water_temp) >= float(self._heat_start_temp or water_temp) + 0.1:
                                lag_min = max(0.0, (now - self._heat_start_ts).total_seconds() / 60.0)
                                if lag_min <= 30:
                                    alpha = 0.2
                                    self.heat_startup_offset_minutes = max(0.0, (1 - alpha) * float(self.heat_startup_offset_minutes) + alpha * lag_min)
                                self._heat_start_reached = True
                        except Exception:
                            pass
                    if not heat_active:
                        self._heat_start_ts = None
                        self._heat_start_temp = None
                        self._heat_start_reached = False
                    self._last_heat_active = heat_active

                    # Persist tuned values occasionally (best effort)
                    if self.entry and self.entry.options:
                        should_save = False
                        try:
                            last_save = self._heat_tuning_last_saved
                            if (last_save is None) or ((now - last_save).total_seconds() >= 15 * 60):
                                should_save = True
                        except Exception:
                            should_save = True
                        if should_save:
                            try:
                                new_opts = {**self.entry.options}
                                new_opts[OPT_KEY_HEAT_LOSS_W_PER_C] = float(self.heat_loss_w_per_c)
                                new_opts[OPT_KEY_HEAT_STARTUP_OFFSET_MINUTES] = float(self.heat_startup_offset_minutes)
                                await self._async_update_entry_options(new_opts)
                                self._heat_tuning_last_saved = now
                            except Exception:
                                pass
            except Exception:
                pass

            # Start calendar-driven bathing: if event is ongoing, ensure manual timer active
            # (in Wartung deaktiviert)
            if (not maintenance_active) and (not self.away_active) and cal_ongoing.get("start") and cal_ongoing.get("end"):
                if now >= cal_ongoing["start"] and now < cal_ongoing["end"]:
                    remaining_min = max(1, int((cal_ongoing["end"] - now).total_seconds() / 60))
                    if (not pause_active) and (not manual_active) and (not event_rain_blocked):
                        await self.activate_manual_timer(timer_type="bathing", minutes=remaining_min)
                        _LOGGER.debug(
                            "Calendar event started -> activate bathing timer (%s) remaining=%smin",
                            getattr(self.entry, "entry_id", None),
                            remaining_min,
                        )
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
                elif min_gap_remaining > 0:
                    shifted = now + timedelta(minutes=int(min_gap_remaining))
                    if shifted != self.next_filter_start:
                        self.next_filter_start = shifted
                        try:
                            new_opts = {**self.entry.options, OPT_KEY_FILTER_NEXT: shifted.isoformat()}
                            await self._async_update_entry_options(new_opts)
                        except Exception:
                            _LOGGER.exception("Fehler beim Umplanen von next_filter_start (min gap)")
                else:
                    # Always start auto-filter when due (PV should not block filtering)
                    # Apply credit: only run missing minutes; if none missing, skip cycle.
                    if filter_missing_minutes <= 0:
                        try:
                            next_start = now + timedelta(minutes=self.filter_interval)
                            self.next_filter_start = next_start
                            self._filter_credit_minutes = 0.0
                            self._filter_credit_expires_at = next_start
                            new_opts = {**self.entry.options, OPT_KEY_FILTER_NEXT: next_start.isoformat()}
                            await self._async_update_entry_options(new_opts)
                        except Exception:
                            _LOGGER.exception("Fehler beim Überspringen von Filterlauf (Credit)")
                    else:
                        await self._start_auto_filter(minutes=filter_missing_minutes)
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

            # Away mode: suppress non-filter manual modes
            if self.away_active and self.manual_timer_type in ("bathing", "chlorine"):
                is_bathing = False
                is_chlorinating = False
                is_manual_heat = False

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
            pv_run = bool(enable_pv and pv_allows and (not in_quiet) and (not maintenance_active) and (not self.away_active) and (pv_heat_demand))

            # Optimiert: manuelle Timer erzwingen "heat"-Modus
            manual_heat_run = is_manual_heat and (not self.away_active)


            # "Preheat" ist nur die Phase VOR einem Kalender-Event, in der wir bereits starten dürfen.
            # Wenn das Event bereits läuft, wird oben automatisch ein bathing-Manual-Timer aktiviert.
            preheat_active = bool(
                (next_start_mins is not None and next_start_mins == 0)
                and cal_next.get("start")
                and now < cal_next["start"]
                and (not event_rain_blocked)
                and (not self.away_active)
            )


            # Thermostat behavior: if PV optimization is disabled, allow heating to maintain target temperature
            # (similar to a normal climate entity), gated by hvac_enabled.
            thermostat_run = bool((not enable_pv) and (not self.away_active) and getattr(self, "hvac_enabled", True))

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
                "away_active": bool(self.away_active),
                "run_reason": run_reason,
                "heat_reason": heat_reason,
                "run_credit_source": self._credit_streak_source if self._credit_streak_source else None,
                "run_credit_minutes": int(round(float(self._credit_streak_minutes or 0.0))),
                "filter_credit_minutes": int(round(float(filter_credit_effective or 0.0))),
                "filter_missing_minutes": int(round(float(filter_missing_minutes or 0))),
                "frost_credit_minutes": int(round(float(frost_credit_effective or 0.0))),
                "frost_credit_shift_minutes": int(round(float(frost_credit_shift or 0))),
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
                "event_rain_probability": event_rain_probability,
                "event_rain_blocked": event_rain_blocked,
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
                # PV band sensors for chart coloring (low/mid/high)
                "pv_band_low": pv_band_low,
                "pv_band_mid_on": pv_band_mid_on,
                "pv_band_mid_off": pv_band_mid_off,
                "pv_band_high": pv_band_high,
                "pv_allows": pv_allows,
                "in_quiet": in_quiet,
                "main_power": round(main_power, 1) if main_power is not None else None,
                "aux_power": round(aux_power, 1) if aux_power is not None else None,
                "electricity_price": round(float(electricity_price), 4) if electricity_price is not None else None,
                "feed_in_tariff": round(float(feed_in_tariff), 4) if feed_in_tariff is not None else None,
                "power_cost_per_hour": round(float(power_cost_per_hour), 4) if power_cost_per_hour is not None else None,
                "power_cost_per_hour_net": round(float(power_cost_per_hour_net), 4) if power_cost_per_hour_net is not None else None,
                "power_cost_feed_in_loss_per_hour": round(float(power_cost_feed_in_loss_per_hour), 4) if power_cost_feed_in_loss_per_hour is not None else None,
                "energy_cost_daily": round(float(energy_cost_daily), 4) if energy_cost_daily is not None else None,
                "energy_cost_monthly": round(float(energy_cost_monthly), 4) if energy_cost_monthly is not None else None,
                "energy_cost_yearly": round(float(energy_cost_yearly), 4) if energy_cost_yearly is not None else None,
                "energy_feed_in_loss_daily": round(float(energy_feed_in_loss_daily), 4) if energy_feed_in_loss_daily is not None else None,
                "energy_feed_in_loss_monthly": round(float(energy_feed_in_loss_monthly), 4) if energy_feed_in_loss_monthly is not None else None,
                "energy_feed_in_loss_yearly": round(float(energy_feed_in_loss_yearly), 4) if energy_feed_in_loss_yearly is not None else None,
                "energy_cost_net_daily": round(float(energy_cost_net_daily), 4) if energy_cost_net_daily is not None else None,
                "energy_cost_net_monthly": round(float(energy_cost_net_monthly), 4) if energy_cost_net_monthly is not None else None,
                "energy_cost_net_yearly": round(float(energy_cost_net_yearly), 4) if energy_cost_net_yearly is not None else None,
                "heat_loss_w_per_c": round(float(self.heat_loss_w_per_c), 2) if self.heat_loss_w_per_c is not None else None,
                "heat_startup_offset_minutes": round(float(self.heat_startup_offset_minutes), 1) if self.heat_startup_offset_minutes is not None else None,
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

                def _can_attempt(entity_id: str, allow_integration: bool = False) -> bool:
                    # No entity configured -> nothing to attempt (caller should handle)
                    if not entity_id:
                        return True
                    # Avoid toggling entities that were created by this integration (would cause feedback loops)
                    if _is_integration_entity(entity_id) and not allow_integration:
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

                # Toggle aux switch according to desired_aux AND aux_allowed
                # aux_allowed ist der Master-Enable: wenn False, bleibt physischer Schalter immer aus
                if aux_switch_id:
                    physical_aux_should_be_on = desired_aux and self.aux_allowed
                    # Prefer toggling the integration's aux switch if present (this calls the physical switch).
                    aux_entity_id = None
                    if ent_reg:
                        try:
                            cand = ent_reg.async_get_entity_id("switch", DOMAIN, f"{self.entry.entry_id}_aux")
                            if cand:
                                ent = ent_reg.async_get(cand)
                                if ent and getattr(ent, "translation_key", None) == "aux":
                                    aux_entity_id = cand
                        except Exception:
                            aux_entity_id = None
                    target_aux_id = aux_entity_id or aux_switch_id
                    allow_integration = bool(aux_entity_id)

                    if physical_aux_should_be_on != self._last_should_aux_on:
                        if physical_aux_should_be_on:
                            if not demo and _can_attempt(target_aux_id, allow_integration=allow_integration):
                                self._last_toggle_attempts[target_aux_id] = now
                                await self._async_turn_entity(target_aux_id, True)
                        else:
                            if not demo and _can_attempt(target_aux_id, allow_integration=allow_integration):
                                self._last_toggle_attempts[target_aux_id] = now
                                await self._async_turn_entity(target_aux_id, False)
                        self._last_should_aux_on = physical_aux_should_be_on
            except Exception:
                _LOGGER.exception("Fehler beim Anwenden der gewünschten Schaltzustände")

            # Track run state for credit accounting (next cycle)
            try:
                current_run_active = bool(data.get("should_pump_on"))
                current_run_source = self._credit_source_from_reasons(run_reason, heat_reason)
                if self._last_run_active and (not current_run_active):
                    self._last_run_end = now
                self._last_run_active = current_run_active
                self._last_run_source = current_run_source
            except Exception:
                pass

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
        except asyncio.CancelledError:
            # Update was cancelled (e.g., overlapping refresh). Keep cached data to
            # avoid entities flipping to unavailable without a useful log trail.
            _LOGGER.warning(
                "Coordinator update cancelled for %s; returning cached data",
                getattr(self.entry, "entry_id", None),
            )
            if getattr(self, "data", None):
                return self.data
            self.data = _safe_defaults
            return self.data
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

    async def _get_hourly_forecast(self, entity_id: str | None):
        """Best-effort fetch hourly forecast for the given weather entity with caching."""
        if not entity_id:
            return None
        try:
            # Cache for 10 minutes to avoid spamming the service.
            cache = getattr(self, "_weather_forecast_cache", None) or {}
            now = dt_util.now()
            fetched_at = cache.get("fetched_at")
            if (
                cache.get("entity_id") == entity_id
                and fetched_at
                and (now - fetched_at) < timedelta(minutes=10)
                and cache.get("forecast") is not None
            ):
                return cache.get("forecast")
        except Exception:
            # ignore cache errors
            pass

        # Ensure the service exists
        if not self.hass.services.has_service("weather", "get_forecasts"):
            return None

        try:
            res = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"entity_id": entity_id, "type": "hourly"},
                blocking=True,
                return_response=True,
            )
        except Exception as err:
            _LOGGER.warning("Weather forecast fetch failed for %s: %s", entity_id, err)
            return None

        forecast = None
        try:
            block = res.get(entity_id) if isinstance(res, dict) else None
            if isinstance(block, dict):
                forecast = block.get("forecast") or block.get("forecasts")
            if forecast is None and isinstance(res, dict):
                forecast = res.get("forecast") or res.get("forecasts")
        except Exception:
            forecast = None

        if not isinstance(forecast, list):
            forecast = None

        try:
            self._weather_forecast_cache = {
                "entity_id": entity_id,
                "fetched_at": dt_util.now(),
                "forecast": forecast,
            }
        except Exception:
            pass

        return forecast

    def _event_rain_check(self, start_dt: datetime | None, end_dt: datetime | None, forecast: list | None, threshold: int):
        """Return (max_probability, blocked) for the event time window."""
        if not start_dt or not forecast:
            return None, False

        try:
            start_utc = dt_util.as_utc(start_dt)
        except Exception:
            start_utc = start_dt

        if end_dt:
            try:
                end_utc = dt_util.as_utc(end_dt)
            except Exception:
                end_utc = end_dt
        else:
            end_utc = start_utc + timedelta(hours=2)

        max_prob = None
        for item in forecast:
            if not isinstance(item, dict):
                continue
            dt_raw = item.get("datetime") or item.get("time") or item.get("forecast_time")
            if not dt_raw:
                continue
            try:
                dt_obj = dt_util.parse_datetime(dt_raw) if isinstance(dt_raw, str) else dt_raw
            except Exception:
                dt_obj = None
            if not dt_obj:
                continue
            try:
                dt_obj = dt_util.as_utc(dt_obj)
            except Exception:
                pass
            if dt_obj < start_utc or dt_obj > end_utc:
                continue
            prob_raw = item.get("precipitation_probability")
            if prob_raw is None:
                continue
            try:
                prob = float(prob_raw)
            except Exception:
                continue
            max_prob = prob if max_prob is None else max(max_prob, prob)

        blocked = (max_prob is not None) and (float(max_prob) >= float(threshold))
        return max_prob, blocked

    async def _check_holiday(self, cal_id):
        if not cal_id: return False
        try:
            res = await self.hass.services.async_call("calendar", "get_events", {"entity_id": cal_id, "start_date_time": dt_util.now().replace(hour=0, minute=0), "end_date_time": dt_util.now().replace(hour=23, minute=59)}, blocking=True, return_response=True)
            return len(res.get(cal_id, {}).get("events", [])) > 0
        except Exception as err:
            _LOGGER.warning("Holiday calendar fetch failed for %s: %s", cal_id, err)
            return False

    async def _get_next_event(self, cal_id):
        if not cal_id:
            return {}

        _LOGGER.debug("Calendar fetch start for %s", cal_id)

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
                _LOGGER.debug("Calendar fetch: no events for %s", cal_id)
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
        except Exception as err:
            _LOGGER.warning("Calendar fetch failed for %s: %s", cal_id, err)
            return {}