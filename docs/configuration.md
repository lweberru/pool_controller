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
  - Main power sensor (kW) for heating calculations
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
- **Min/Max/Step**: UI bounds for the thermostat entity
- **Tolerances**: Simple hysteresis (cold/hot tolerance)

### Step 6: Frost Protection
- **Outdoor Temperature Sensor**: For frost protection logic
- **Frost Protection Tuning** (optional): duty-cycle settings and a quiet-hours emergency threshold

### Step 7: Calendar & Quiet Hours
- **Pool Calendar**: Calendar entity for operation schedule
- **Holiday Calendar**: Calendar used to treat local holidays like weekends (weekend quiet hours apply)
- **Quiet Hours (Weekdays)**: Start/end times (e.g., 22:00 - 07:00)
- **Quiet Hours (Weekends)**: Start/end times

### Step 8: Filter Settings
- **Automatic filtering**: Enable/disable automatic filter cycles
- **Filter Interval**: Minutes between automatic filter cycles (default: 720 = 12 hours)

### Step 9: PV Solar Integration
- **PV Surplus Sensor**: Entity measuring excess solar production (W)
- **PV ON Threshold**: Turns pump/heating on when PV power >= threshold (default: 1000W)
- **PV OFF Threshold**: Turns pump/heating off when PV power <= threshold (default: 500W)

## Configuration Options & Defaults

| Setting | Default | Range | Notes |
|---------|---------|-------|-------|
| Water Volume | 1000 | 100-10000 L | Used for pH/Chlorine dosing calculations |
| Sanitizer Mode | chlorine | chlorine / saltwater / mixed | Affects how TDS is interpreted (effective TDS for saltwater/mixed) |
| Target Salt (g/L) | 4.0 | 0-10 g/L | Only used for saltwater/mixed; baseline for effective TDS |
| Filter Interval | 720 | 60-10080 min | Time between automatic filter cycles |
| Filter Duration | 30 | 5-480 min | How long each filter cycle runs |
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
| Min Temp | 10°C | - | Climate min temp bound |
| Max Temp | 40°C | - | Climate max temp bound |
| Temperature Step | 0.5°C | - | Climate target temperature step |
| Cold Tolerance | 1.0°C | - | Hysteresis: turn ON below (target - cold) |
| Hot Tolerance | 0.0°C | - | Hysteresis: keep ON until (target + hot) |
| Quick Chlorine Duration | 5 | 1-30 min | Duration of chlorine boost |
| PV ON Threshold | 1000 | 0-20000 W | Enable PV operation above this surplus |
| PV OFF Threshold | 500 | 0-20000 W | Disable PV operation below this surplus |

All duration settings can be overridden per operation via **Services**.
