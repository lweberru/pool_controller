# Advanced Features

[← Back to README](../README.md)

## Filtration Logic
- **Auto-filtering**: Runs on configurable interval
- **Smart scheduling**: Respects quiet hours and frost danger
- **Manual override**: Start/stop via buttons or services
- **Duration control**: Adjustable per cycle
- **Run credit**: Minutes already run can reduce or shift future runs
- **Merge window**: When a frost run is close, filter + frost can merge into a single run
- **Minimum gap**: Enforces a rest period between runs (except severe frost)

### Run Credit (Filter + Frost)

The controller tracks **eligible run minutes** (credit). If a recent run already covered part of the needed filter or frost time, the next run can be shortened or shifted.

- **Credit Sources** decide which run reasons count (e.g., `filter`, `bathing`, `chlorine`, `preheat`, `pv`, `frost`, `thermostat`).
- **Minimum Credit** ignores very short runs (noise).
- **Filter credit** reduces the *next* auto-filter duration (or skips it if fully covered).
- **Frost credit** can shift mild frost cycles later to reduce noise.

This improves efficiency by avoiding redundant runs while keeping protection targets intact.

#### Flow: How bathing/PV affects the next filter run

```mermaid
flowchart TD
	A[Coordinator update cycle] --> B[Determine run_reason / heat_reason]
	B --> C{Source in credit_sources?}
	C -- yes --> D[_update_run_credit adds minutes]
	C -- no --> E[No credit added]
	D --> F[Compute filter_credit_effective]
	E --> F
	F --> G[Filter due? (now >= next_filter_start)]
	G -- no --> H[No change to schedule]
	G -- yes --> I{Maintenance/Pause/Quiet hours?}
	I -- yes --> J[next_filter_start shifted to quiet end]
	I -- no --> K{min_gap_remaining > 0?}
	K -- yes --> L[next_filter_start = now + min_gap]
	K -- no --> M{filter_missing_minutes <= 0?}
	M -- yes --> N[Skip run; next_filter_start = now + filter_interval]
	M -- no --> O[Start auto-filter for filter_missing_minutes]
```

#### Example 1: PV run creates credit and skips the next filter

**Setup:**
- `filter_interval_minutes = 720` (12h)
- `filter_minutes = 30`
- `credit_sources` includes `pv`

**Scenario:**
1. The pool runs for **30 minutes** due to **PV surplus**.
2. Those minutes are added to `filter_credit_minutes`.
3. When the next filter time is reached, `filter_missing_minutes <= 0`.

**Result:** The filter run is skipped and `next_filter_start` is moved to **now + 12h**.

#### Example 2: Bathing run creates partial credit and shortens the next filter

**Setup:**
- `filter_interval_minutes = 720` (12h)
- `filter_minutes = 40`
- `credit_sources` includes `bathing`

**Scenario:**
1. A **20‑minute bathing session** runs.
2. Those minutes are counted as credit.
3. When the next filter time is reached, `filter_missing_minutes = 20`.

**Result:** The auto‑filter starts but runs for **20 minutes** instead of 40.

## Temperature Control & Water Volume Calculations

The **water volume** setting is critical for automated calculations.

### Heating Time Calculation

**Formula:**

```
Time (minutes) = (Water Volume (L) × 1.16 × ΔT (°C)) / Power (W) × 60

Where:
- 1.16 = Specific heat capacity of water (Wh/L/°C)
- ΔT = Target temperature - Current water temperature
- Power = Heater power consumption (from configured model)
```

### Temperature Control (Extended)

**Heating enabled when:**
- ✅ Pool not paused
- ✅ Not in frost protection mode
- ✅ Calendar preheat / bathing / PV surplus allows heating

## Calendar Events & Weather Guard

The integration can **preheat** before calendar events and start a **bathing session** while the event is ongoing.
If the **Weather Guard** is enabled, it checks the hourly forecast and **skips both preheat and event start** when rain is likely during the event.

**How it works:**
- The system reads the next/ongoing calendar event window.
- It fetches hourly forecast data via `weather.get_forecasts`.
- It calculates the **maximum rain probability** during the event.
- If that probability is **>= the configured threshold**, the event is blocked.

**Relevant entities:**
- `sensor.<pool>_event_rain_probability`
- `binary_sensor.<pool>_event_rain_blocked`

**Example:**

```yaml
# Settings (Options → Calendar step)
enable_event_weather_guard: true
event_weather_entity: weather.home
event_rain_probability: 60
```

## PV Solar Optimization

When connected to solar:
- Heating only engages if excess PV production > ON threshold
- Heating stops when excess drops below OFF threshold
- Maximizes self-consumption of solar energy

## Quiet Hours

Prevents noisy operations during sensitive times:
- Weekday quiet hours and weekend quiet hours
- Holidays are treated like weekends
- Quiet hours are respected by frost protection by default; an optional emergency threshold can allow frost cycling in extreme cold

## Frost Protection

When outdoor temperature drops below the configured frost start temperature:
- ⚠️ `binary_sensor.<pool>_frost_danger` turns on (risk)
- ✅ Pump requests are duty-cycled via `binary_sensor.<pool>_frost_active`
- ✅ During quiet hours the duty-cycle stays off by default; it only overrides quiet hours if outdoor temperature is below the configured emergency threshold

### Next frost protection run (countdown)

For dashboards, the integration also exposes:

- `sensor.<pool>_next_frost_mins`: minutes until the next **frost protection duty-cycle run starts**.

Notes:
- This is a best-effort estimate (based on the configured duty-cycle interval and quiet hours).
- It is **not** a weather forecast (“next frost”); it only appears when frost protection conditions apply.

## Optional Features

### Auxiliary Heating
If you've added an extra heater (resistive, heat pump, etc.):
1. Configure a secondary smart switch entity during setup
2. Switch appears as `switch.pool_aux_allowed`
3. Controls whether the auxiliary heater is currently allowed (feature enable)

### Salt Water Chlorination
If your pool uses salt chlorination:
- Configure salt sensor from Blueriiot
- Integration tracks salt levels
- Helps maintain proper electrolysis conditions
