# Changelog

All notable changes to this integration are documented in this file.

## [2.3.6] - 2026-01-30
- Make daily cost sensors time-weighted and monotonic within the day (tariff applied at time of consumption).
- Derive monthly/yearly costs from daily totals to avoid tariff retroactive changes.

## [2.3.5] - 2026-01-30
- Auto-derive monthly/yearly energy totals from daily sensors when missing.
- Auto-detect AlphaESS energy sensors as defaults in the costs step.
- Clarify cost input descriptions for optional month/year fields.

## [2.3.4] - 2026-01-30
- Add daily/monthly/yearly energy inputs and cost/net cost sensors.
- Expose PV opportunity-cost (feed-in loss) period variants.
- Update translations for new costs/energy fields.

## [2.3.3] - 2026-01-29
- Fix English translation formatting and sync options/costs labels.
- Add missing costs menu/step labels in French options translations.

## [2.3.2] - 2026-01-29
- Fix options menu label for costs and add missing costs-step titles/descriptions in translations.

## [2.3.1] - 2026-01-29
- Move costs configuration to a dedicated step at the end of setup and options flow.
- Allow `input_number` helpers for electricity price and feed-in tariff entities.
- Costs are fully optional; if not configured, cost sensors remain empty.

## [2.3.0] - 2026-01-29
- Add electricity cost estimation with fixed/dynamic price and feed-in tariff.
- New diagnostic sensors: `electricity_price`, `feed_in_tariff`, `power_cost_per_hour`, `power_cost_per_hour_net`, `power_cost_feed_in_loss_per_hour`.

## [2.2.9] - 2026-01-27
- Persist filter/frost run credits across Home Assistant restarts (best-effort, throttled).

## [2.2.8] - 2026-01-26
- Adaptive heating tuning: auto-learned heat loss coefficient and startup offset.
- Updated preheat estimation to use effective heating power (loss-adjusted).
- New diagnostic sensors: `heat_loss_w_per_c` and `heat_startup_offset_minutes`.
- Heat-loss tuning uses a minimum 60‑minute window to handle sparse temperature updates.

## [1.6.30] - 2026-01-12
- Add `binary_sensor.<pool>_aux_present` — indicates whether an auxiliary heater is configured (true when `enable_aux_heating` is set or an `aux_heating_switch` is configured).
- Minor docs update to list the new binary sensor.

For previous changes see release tags on GitHub.
# Changelog

This project is released via GitHub Releases (HACS). Tags follow `vX.Y.Z`.

## Recent Updates

### v1.6.17 (Jan 2026)
- Add `sensor.*_outdoor_temp` and `sensor.*_next_frost_mins` for better frost protection observability (next duty-cycle run countdown).
- Clarify translations so `next_frost_mins` reads as “next frost protection run”, not “next frost”.

### v1.6.13 (Jan 2026)
- Expose physical switch states as binary sensors (`*_main_switch_on`, `*_pump_switch_on`, `*_aux_heating_switch_on`) for transparency in dashboards.

### v1.6.12 (Jan 2026)
- Split heating power model for preheat estimation (base + auxiliary heater contribution).

### v1.6.11 (Jan 2026)
- Fix preheat countdown by using configured heater power for estimation (no longer derived from a live power sensor).

### v1.6.10 (Jan 2026)
- Heating is now gated by explicit reasons (calendar preheat / PV surplus / bathing), plus new observability via `run_reason` / `heat_reason` sensors.

### v1.5.7 (Jan 2026)
- Updated strings.json with English as default fallback language
- Complete synchronization with translations/en.json
- Improved international usability

### v1.5.6 (Jan 2026)
- Fixed Feature Flag labels in config flow (removed verbose "Enable" prefix)
- Added comprehensive data_description for all Feature Flags
- Complete Options Flow integration for all toggles
- All changes in 4 languages (de, en, es, fr)

### v1.5.5 (Jan 2026)
- TDS maintenance monitoring with intelligent water change recommendations
- 5-tier TDS status system (optimal/good/high/critical/urgent)
- Automatic water change calculations (liters and percent)
- Binary sensor for TDS warnings

### v1.5.4 (Jan 2026)
- Salt and TDS sensors with automatic μS/cm → ppm conversion
- Saltwater pool support
- TDS conversion factor: 0.64 (standard pool water)

### v1.5.3 (Jan 2026)
- Comprehensive field descriptions for all config flow parameters
- Improved UX with data_description for 56+ fields
- Multi-language support for all descriptions

### v1.5.2 (Jan 2026)
- Added quick_chlorine_until timer sensor
- Complete timer visualization support for dashboard
