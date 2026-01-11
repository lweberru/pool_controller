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
