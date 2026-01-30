# Sensors, Entities & Controls

[← Back to README](../README.md)

Entity IDs depend on your instance name, but the integration uses stable suffix keys (translation_key / unique_id suffixes) as shown below.

## Binary Sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.<pool>_is_we_holiday` | True if today is weekend or holiday |
| `binary_sensor.<pool>_frost_danger` | True when outdoor temp is below the configured frost start temperature |
| `binary_sensor.<pool>_frost_active` | True when the frost duty-cycle currently requests the pump to run |
| `binary_sensor.<pool>_in_quiet` | Quiet hours active |
| `binary_sensor.<pool>_pv_allows` | PV surplus available for operation |
| `binary_sensor.<pool>_should_main_on` | Power supply should be on |
| `binary_sensor.<pool>_should_pump_on` | Circulation pump should be on |
| `binary_sensor.<pool>_main_switch_on` | Physical main switch is currently ON (mirrors the configured external switch state) |
| `binary_sensor.<pool>_pump_switch_on` | Physical pump switch is currently ON (mirrors the configured external switch state) |
| `binary_sensor.<pool>_aux_heating_switch_on` | Physical auxiliary heater switch is currently ON (mirrors the configured external switch state) |
| `binary_sensor.<pool>_aux_present` | Auxiliary heater configured (true when `enable_aux_heating` is set or an aux switch is configured) |
| `binary_sensor.<pool>_low_chlor` | Chlorine below recommended level |
| `binary_sensor.<pool>_ph_alert` | pH outside acceptable range |
| `binary_sensor.<pool>_tds_high` | TDS too high (water change needed) |
| `binary_sensor.<pool>_event_rain_blocked` | True when the next/ongoing calendar event is blocked due to rain probability |

## Sensors (Numeric & Status)

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.<pool>_status` | Enum | Current state: `normal`, `paused`, `frost_protection` |
| `sensor.<pool>_run_reason` | Enum | Why the pool is running right now: `idle`, `bathing`, `chlorine`, `filter`, `preheat`, `pv`, `frost`, `pause`, `maintenance` |
| `sensor.<pool>_heat_reason` | Enum | Why heating is allowed/active: `off`, `disabled`, `bathing`, `preheat`, `pv` |
| `sensor.<pool>_run_credit_source` | Enum | Current credit source (if a streak is active) |
| `sensor.<pool>_run_credit_minutes` | Integer | Minutes credited from the current streak |
| `sensor.<pool>_filter_credit_minutes` | Integer | Effective filter credit minutes |
| `sensor.<pool>_filter_missing_minutes` | Integer | Remaining filter minutes needed for the next cycle |
| `sensor.<pool>_frost_credit_minutes` | Integer | Effective frost credit minutes |
| `sensor.<pool>_frost_credit_shift_minutes` | Integer | Minutes the frost cycle is shifted due to credit |
| `sensor.<pool>_electricity_price` | Float | Electricity price (currency per kWh) |
| `sensor.<pool>_feed_in_tariff` | Float | Feed-in tariff (currency per kWh) |
| `sensor.<pool>_power_cost_per_hour` | Float | Instantaneous power cost (per hour) |
| `sensor.<pool>_power_cost_per_hour_net` | Float | Instantaneous net power cost (per hour; PV surplus deducted) |
| `sensor.<pool>_power_cost_feed_in_loss_per_hour` | Float | Instantaneous lost feed-in revenue (per hour) |
| `sensor.<pool>_energy_grid_to_load_kwh` | Float | Grid → load energy (kWh) for the selected period (from utility meter or energy sensor) |
| `sensor.<pool>_energy_grid_to_load_kwh_daily` | Float | Grid → load energy (kWh) for the day |
| `sensor.<pool>_energy_grid_to_load_kwh_monthly` | Float | Grid → load energy (kWh) for the month |
| `sensor.<pool>_energy_grid_to_load_kwh_yearly` | Float | Grid → load energy (kWh) for the year |
| `sensor.<pool>_energy_solar_to_grid_kwh` | Float | Solar → grid energy (kWh) for the selected period |
| `sensor.<pool>_energy_solar_to_load_kwh` | Float | Solar → load energy (kWh) for the selected period |
| `sensor.<pool>_energy_solar_to_load_kwh_daily` | Float | Solar → load energy (kWh) for the day |
| `sensor.<pool>_energy_solar_to_load_kwh_monthly` | Float | Solar → load energy (kWh) for the month |
| `sensor.<pool>_energy_solar_to_load_kwh_yearly` | Float | Solar → load energy (kWh) for the year |
| `sensor.<pool>_energy_total_load_kwh` | Float | Total load energy (kWh) for the selected period |
| `sensor.<pool>_energy_cost` | Float | Energy cost for the selected period (based on grid → load energy) |
| `sensor.<pool>_energy_cost_net` | Float | Net energy cost for the selected period (grid cost + PV opportunity cost) |
| `sensor.<pool>_energy_cost_daily` | Float | Energy cost for the day (based on grid → load energy) |
| `sensor.<pool>_energy_cost_monthly` | Float | Energy cost for the month (based on grid → load energy) |
| `sensor.<pool>_energy_cost_yearly` | Float | Energy cost for the year (based on grid → load energy) |
| `sensor.<pool>_energy_feed_in_loss` | Float | PV opportunity cost for the selected period (based on solar → load energy) |
| `sensor.<pool>_energy_feed_in_loss_daily` | Float | PV opportunity cost for the day |
| `sensor.<pool>_energy_feed_in_loss_monthly` | Float | PV opportunity cost for the month |
| `sensor.<pool>_energy_feed_in_loss_yearly` | Float | PV opportunity cost for the year |
| `sensor.<pool>_energy_cost_net_daily` | Float | Net energy cost for the day |
| `sensor.<pool>_energy_cost_net_monthly` | Float | Net energy cost for the month |
| `sensor.<pool>_energy_cost_net_yearly` | Float | Net energy cost for the year |
| `sensor.<pool>_heat_loss_w_per_c` | Float | Learned heat loss coefficient (W/°C) |
| `sensor.<pool>_heat_startup_offset_minutes` | Float | Learned heating startup delay (minutes) |
| `sensor.<pool>_sanitizer_mode` | Enum | Disinfection style: `chlorine`, `saltwater`, `mixed` |
| `sensor.<pool>_tds_status` | Enum | Water quality assessment (backend-derived) |
| `sensor.<pool>_ph_val` | Float | Water pH (0-14) |
| `sensor.<pool>_chlor_val` | Float | Chlorine/ORP in mV |
| `sensor.<pool>_salt_val` | Float | Salt concentration in g/L (optional) |
| `sensor.<pool>_salt_add_g` | Integer | Recommended salt to add in grams (saltwater/mixed only; 0 when OK/not applicable) |
| `sensor.<pool>_tds_val` | Integer | Total Dissolved Solids (TDS) in ppm (optional) |
| `sensor.<pool>_tds_effective` | Integer | Effective TDS in ppm (saltwater/mixed only; salt baseline subtracted) |
| `sensor.<pool>_tds_water_change_liters` | Integer | Recommended water change volume (liters) |
| `sensor.<pool>_tds_water_change_percent` | Integer | Recommended water change (%) |
| `sensor.<pool>_ph_minus_g` | Float | Recommended pH- dosage in grams |
| `sensor.<pool>_ph_plus_g` | Float | Recommended pH+ dosage in grams |
| `sensor.<pool>_chlor_spoons` | Float | Recommended chlorine dosage in spoons |
| `sensor.<pool>_next_start_mins` | Integer | Minutes until next operation |
| `sensor.<pool>_next_frost_mins` | Integer | Minutes until the next **frost protection run starts** (duty-cycle; best-effort) |
| `sensor.<pool>_outdoor_temp` | Float | Outdoor temperature in °C (used for frost protection logic) |
| `sensor.<pool>_next_event` | Timestamp | Next calendar event start |
| `sensor.<pool>_next_event_end` | Timestamp | Next calendar event end |
| `sensor.<pool>_next_event_summary` | String | Next calendar event name |
| `sensor.<pool>_event_rain_probability` | Float | Max rain probability during the next/ongoing event (0–100) |
| `sensor.<pool>_next_filter_mins` | Integer | Minutes until next filter cycle |
| `sensor.<pool>_manual_timer_mins` | Integer | Remaining minutes of the active manual timer (bathing/filter/chlorine). Attributes: `active`, `duration_minutes`, `type` |
| `sensor.<pool>_auto_filter_timer_mins` | Integer | Remaining minutes of the automatic filter cycle timer. Attributes: `active`, `duration_minutes` |
| `sensor.<pool>_pause_timer_mins` | Integer | Remaining minutes of the pause timer. Attributes: `active`, `duration_minutes` |
| `sensor.<pool>_frost_timer_mins` | Integer | Remaining minutes of the active frost cycle (if any). Attributes: `active`, `duration_minutes` |
| `sensor.<pool>_pv_power` | Float | PV power (W) derived from the configured PV sensor |
| `sensor.<pool>_pv_smoothed` | Float | Smoothed PV power (W) used for PV hysteresis |
| `sensor.<pool>_pv_band_low` | Float | PV power in low band (≤ OFF threshold) |
| `sensor.<pool>_pv_band_mid_on` | Float | PV power in mid band while PV is allowed (ON state) |
| `sensor.<pool>_pv_band_mid_off` | Float | PV power in mid band while PV is not allowed (OFF state) |
| `sensor.<pool>_pv_band_high` | Float | PV power in high band (≥ ON threshold) |
| `sensor.<pool>_pv_on_threshold` | Integer | Configured PV ON threshold (W) |
| `sensor.<pool>_pv_off_threshold` | Integer | Configured PV OFF threshold (W) |
| `sensor.<pool>_main_power` | Float | Main pump power consumption (W) |
| `sensor.<pool>_aux_power` | Float | Auxiliary heater power consumption (W) |

### Timer sensor attributes (minute-based timers)

All three timer sensors use **minutes remaining** as their state (unit: `min`).

- **State (`sensor.*_timer_mins`)**: integer minutes remaining. When inactive, the state is `0`.
- **Update cadence**: derived from persisted `*_until` timestamps and refreshed by the coordinator (default every 30s). The state decreases over time and can be slightly “stepwise” due to polling.

**Common attribute:**
- `active` (bool): `true` while the timer is considered active, otherwise `false`.

**Manual timer (`sensor.<pool>_manual_timer_mins`) attributes:**
- `type` (string | null): one of `bathing`, `filter`, `chlorine` while active; can be `null` when inactive.
- `duration_minutes` (int | null): the originally requested duration in minutes.

**Auto-filter timer (`sensor.<pool>_auto_filter_timer_mins`) attributes:**
- `duration_minutes` (int | null): the configured/started auto-filter run duration.

**Pause timer (`sensor.<pool>_pause_timer_mins`) attributes:**
- `duration_minutes` (int | null): the requested pause duration.

**Frost timer (`sensor.<pool>_frost_timer_mins`) attributes:**
- `duration_minutes` (int | null): the configured run duration for the current frost cycle.

## Switches

| Entity | Description |
|--------|-------------|
| `switch.<pool>_main` | Power supply / main relay on/off |
| `switch.<pool>_pump` | Circulation pump on/off (may point to the same physical entity as `main` if not configured separately) |
| `switch.<pool>_aux_allowed` | Allow auxiliary heater (feature enable; not the physical heater switch) |
| `switch.<pool>_aux` | Auxiliary heater physical power switch (configured `aux_heating_switch`) |

## Climate

| Entity | Description |
|--------|-------------|
| `climate.<pool>_*` | Pool heater thermostat entity (select this as the controller entity in automations and the dashboard card) |

## Buttons & Manual Controls

The integration provides four quick-action buttons (one per topic, using the default duration):

- `button.<pool>_bath_60` - Start bathing session (60 min)
- `button.<pool>_filter_30` - Start filter cycle (30 min)
- `button.<pool>_chlorine_5` - Start quick chlorine (5 min)
- `button.<pool>_pause_60` - Start pause (60 min)

## Status Sensors & Debugging

### Useful Diagnostic Sensors
- `sensor.pool_next_start_mins` - When next operation starts
- `sensor.pool_next_frost_mins` - When the next frost protection duty-cycle run starts (minutes)
- `sensor.pool_next_event` - Next calendar event
- `sensor.pool_run_reason` - Why the pool is running (idle/bathing/filter/chlorine/preheat/pv/frost/...)
- `sensor.pool_heat_reason` - Why heating is allowed (off/disabled/bathing/preheat/pv)
- `sensor.pool_run_credit_source` - Current credit source (if any)
- `sensor.pool_run_credit_minutes` - Current credited minutes
- `sensor.pool_filter_credit_minutes` - Effective filter credit
- `sensor.pool_filter_missing_minutes` - Remaining minutes needed for filter
- `sensor.pool_frost_credit_minutes` - Effective frost credit
- `sensor.pool_frost_credit_shift_minutes` - Frost shift minutes
- `sensor.pool_heat_loss_w_per_c` - Learned heat loss coefficient (W/°C)
- `sensor.pool_heat_startup_offset_minutes` - Learned heating startup delay (minutes)
- `sensor.pool_outdoor_temp` - Outdoor temperature (input for frost protection)
- `binary_sensor.pool_should_main_on` - Power supply requested
- `binary_sensor.pool_should_pump_on` - Pump requested
- `binary_sensor.pool_main_switch_on` - Physical main switch ON (mirror)
- `binary_sensor.pool_pump_switch_on` - Physical pump switch ON (mirror)
- `binary_sensor.pool_aux_heating_switch_on` - Physical aux heater switch ON (mirror)

Enable debug logging in Home Assistant:

```yaml
logger:
  logs:
    custom_components.pool_controller: debug
```
