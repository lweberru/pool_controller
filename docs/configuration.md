# Configuration

[← Back to README](../README.md)

## Configuration Flow

The integration uses a guided wizard (9–10 steps depending on sanitizer mode):

### Step 1: Basic Information
- **Name**: Display name for your pool (e.g., "Whirlpool Demo")
- **Water Volume**: Liters of water (used for pH/chlorine calculations)
- **Demo Mode**: Enable to test without actual devices

### Step 2: Switches & Power Sensors
- **Main Switch**: Power supply / main relay (required)
- **Pump Switch**: Circulation pump (optional; if omitted, the integration uses the main switch)
- **Auxiliary Heating Switch**: Secondary heater (optional)
- **Power Sensors**:
  - Main power sensor (W) for heating calculations
  - Auxiliary power sensor (optional)

### Step 3: Water Quality Sensors (Optional)
Configure only if using ESP32 + Blueriiot:
- **Water Temperature Sensor**: Current pool water temperature
- **pH Sensor**: Water pH value (0-14)
- **Chlorine Sensor**: Redox/ORP value (mV)
- **Salt Sensor**: Salt concentration (g/L) - optional
- **Conductivity Sensor**: µS/cm - optional

### Step 4: Sanitizer / Disinfection
Pool Controller supports different disinfection styles and adapts some water-quality interpretation accordingly.

- **Sanitizer Mode**: `chlorine`, `saltwater`, or `mixed` (salt + chlorine)
- **Step 4b (Saltwater/Mixed only)**: **Target Salt (g/L)** (used as a baseline for effective TDS)

### Step 5: Temperature Control (Thermostat)
- **Target Temp**: Desired water temperature (persisted)
- **Away Temperature**: Target temperature used when Away mode is active
- **Min/Max/Step**: UI bounds for the thermostat entity
- **Tolerances**: Simple hysteresis (cold/hot tolerance)

**Away mode behavior**:
- Sets the target temperature to **Away Temperature**
- Stops manual timers and pause
- Keeps automatic filtering and frost protection active

### Step 6: Frost Protection
- **Outdoor Temperature Sensor**: For frost protection logic
- **Frost Protection Tuning** (optional): duty-cycle settings and a quiet-hours emergency threshold

### Step 7: Calendar & Quiet Hours
- **Pool Calendar**: Calendar entity for operation schedule
- **Holiday Calendar**: Calendar used to treat local holidays like weekends (weekend quiet hours apply)
- **Weather Guard (Optional)**:
  - **Enable Weather Guard**: Skip preheat and event start if rain is likely
  - **Weather Entity**: `weather.*` entity that supports `weather.get_forecasts` (hourly)
  - **Rain Probability Threshold**: If the forecasted probability during the event is >= this value, the event is blocked
- **Quiet Hours (Weekdays)**: Start/end times (e.g., 22:00 - 07:00)
- **Quiet Hours (Weekends)**: Start/end times

**Example (Weather Guard):**

```yaml
# Example: block pool events if rain probability >= 60%
pool_controller:
  # ... your existing setup ...
  enable_event_weather_guard: true
  event_weather_entity: weather.home
  event_rain_probability: 60
```

### Step 8: Filter Settings
- **Automatic filtering**: Enable/disable automatic filter cycles
- **Filter Interval**: Minutes between automatic filter cycles (default: 720 = 12 hours)
- **Filter Duration**: Default run length for one cycle (minutes)
- **Merge Window**: If a frost run is close, filter + frost can merge into one run
- **Minimum Gap**: Enforces a rest period between runs (except severe frost)
- **Max Merged Run**: Upper limit for merged runs
- **Minimum Credit**: Runs shorter than this do **not** count as credit
- **Credit Sources**: Which run reasons count as credit (filter/bathing/chlorine/preheat/pv/frost/thermostat)

### Step 9: PV Solar Integration
- **PV Surplus Sensor**: Entity measuring excess solar production (W)
- **PV ON Threshold**: Turns pump/heating on when PV power >= threshold (default: 1000W)
- **PV OFF Threshold**: Turns pump/heating off when PV power <= threshold (default: 500W)
- **PV Smoothing Window**: Exponential smoothing window (seconds)
- **PV Stability Window**: How long the smoothed value must persist before a state change (seconds)
- **PV Minimum Run**: Minimum run time after an automatic PV start (minutes)

### Step 10: Electricity Costs
- **Electricity Price**: Fixed price (per kWh)
- **Electricity Price Entity**: Dynamic price entity (overrides fixed price)
- **Feed-in Tariff**: Fixed export tariff (per kWh)
- **Feed-in Tariff Entity**: Dynamic export tariff entity (overrides fixed tariff)
- **Pool Energy (Base/Aux)**: Total kWh counters (required for cost tracking)
- **Pool Energy (Base/Aux Daily)**: Optional daily kWh sensors
- **Solar Energy Daily**: Optional daily solar kWh allocated to the pool (used for net cost)

## Configuration Options & Defaults

| Setting | Default | Range | Notes |
|---------|---------|-------|-------|
| Water Volume | 1000 | 100-10000 L | Used for pH/Chlorine dosing calculations |
| Sanitizer Mode | chlorine | chlorine / saltwater / mixed | Affects how TDS is interpreted (effective TDS for saltwater/mixed) |
| Target Salt (g/L) | 4.0 | 0-10 g/L | Only used for saltwater/mixed; baseline for effective TDS |
| Filter Interval | 720 | 60-10080 min | Time between automatic filter cycles |
| Filter Duration | 30 | 5-480 min | How long each filter cycle runs |
| Merge Window | 90 | 0-720 min | If a frost run is within this window, runs may be merged |
| Minimum Gap | 45 | 0-360 min | Rest time between runs (except severe frost) |
| Max Merged Run | 40 | 5-360 min | Upper limit for a merged run |
| Minimum Credit | 5 | 0-60 min | Runs shorter than this do not count as credit |
| Credit Sources | bathing, filter, frost, preheat, pv, thermostat, chlorine | list | Which run reasons contribute credit |
| Bathing Duration | 60 | 5-480 min | Default bathing session length |
| Pause Duration | 60 | 5-480 min | Default pause duration |
| Frost Start Temp | 2°C | -20 to 10°C | Below this outdoor temperature `frost_danger` can become active |
| Frost Severe Temp | -2°C | -30 to 5°C | Below this temperature the severe duty-cycle is used |
| Frost Mild Interval | 240 | 1-1440 min | Mild duty-cycle interval (minutes) |
| Frost Mild Run | 5 | 0-120 min | Run time within the mild interval (minutes) |
| Frost Severe Interval | 120 | 1-1440 min | Severe duty-cycle interval (minutes) |
| Frost Severe Run | 10 | 0-240 min | Run time within the severe interval (minutes) |
| Quiet Override Below | -8°C | -30 to 0°C | During quiet hours frost cycling stays off unless outdoor temp is <= this value |
| Heating Temp Target | 38°C | 10-40°C | Target water temperature (persisted) |
| Away Temperature | 25°C | 10-40°C | Target temperature while Away mode is active |
| Min Temp | 10°C | - | Climate min temp bound |
| Max Temp | 40°C | - | Climate max temp bound |
| Temperature Step | 0.5°C | - | Climate target temperature step |
| Cold Tolerance | 1.0°C | - | Hysteresis: turn ON below (target - cold) |
| Hot Tolerance | 0.0°C | - | Hysteresis: keep ON until (target + hot) |
| Quick Chlorine Duration | 5 | 1-30 min | Duration of chlorine boost |
| PV ON Threshold | 1000 | 0-20000 W | Enable PV operation above this surplus |
| PV OFF Threshold | 500 | 0-20000 W | Disable PV operation below this surplus |
| PV Smoothing Window | 60 | 0-3600 s | Exponential smoothing window (0 disables) |
| PV Stability Window | 120 | 0-86400 s | Required stability before a state change |
| PV Minimum Run | 10 | 0-1440 min | Minimum run time after PV start |
| Electricity Price | 0.30 | 0-5 | Fixed price (currency per kWh) |
| Electricity Price Entity | - | sensor/input_number | Dynamic price entity (overrides fixed) |
| Feed-in Tariff | 0.08 | 0-5 | Fixed export tariff (currency per kWh) |
| Feed-in Tariff Entity | - | sensor/input_number | Dynamic tariff entity (overrides fixed) |
| Pool Energy Base | - | sensor | Total kWh counter for base load |
| Pool Energy Aux | - | sensor | Total kWh counter for aux heater |
| Pool Energy Base Daily | - | sensor | Daily kWh sensor for base load |
| Pool Energy Aux Daily | - | sensor | Daily kWh sensor for aux heater |
| Solar Energy Daily | - | sensor | Daily solar kWh allocated to the pool |

All duration settings can be overridden per operation via **Actions**.
