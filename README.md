# Pool Controller - Advanced Home Assistant Integration

![Latest Version](https://img.shields.io/github/v/release/lweberru/pool_controller)
![License](https://img.shields.io/badge/license-MIT-blue)

## Overview

**Pool Controller** is a Home Assistant custom integration designed to manage and automate your spa or pool when the device lacks built-in smart capabilities. This integration recreates the essential functions of modern pool controllers while adding sophisticated comfort and efficiency features.

### Why Pool Controller?

If your spa or pool is connected to a simple smart switch (on/off only), you lose access to important automation features:
- ❌ Automatic filtration cycles
- ❌ Temperature control
- ❌ Frost protection
- ❌ Water quality monitoring
- ❌ Scheduled maintenance

**Pool Controller** brings all these features back—and adds much more.

---

## Core Features

### Essential Pool Functions
- **Filtration Cycles**: Automatic or manual filter running with configurable intervals and duration
- **Temperature Control**: Smart heating based on calendar events and PV solar production
- **Frost Protection**: Automatic pump activation when outdoor temperature drops below 3°C
- **Water Quality Monitoring**: Integration with ESP32 + Blueriiot sensors for real-time water parameters

### Comfort & Efficiency Features
- **Bath Calendar Integration**: Automatically enable/disable pool operation based on calendar events
- **Quiet Hours**: Define noise restrictions during weekdays and weekends (respects local holidays)
- **PV Solar Integration**: Prioritize heating when solar production exceeds a threshold
- **Quick Chlorine**: One-button chlorination with 5-minute automation
- **Pause Function**: Temporarily pause all pool functions (30-120 minutes)
- **Bath Sessions**: Schedule dedicated bathing sessions with custom durations
- **Auxiliary Heating** (Optional): Control additional heating elements via secondary smart switch

---

## Hardware Requirements

### Essential
1. **Smart Switch** for main pool pump (on/off relay, WiFi/Zigbee compatible with HA)
2. **Home Assistant** instance with custom components support
3. **Optional: Temperature Sensors** 
   - Water temperature (for heating calculations)
   - Outdoor temperature (for frost protection)

### For Water Quality Monitoring (Optional but Recommended)
1. **ESP32 Microcontroller** (e.g., ESP32-S3-DevKitC-1)
2. **Blueriiot Sensor** ([Blue Connect GO](https://www.blueriiot.com/eu-en/products/blue-connect-go))
   - Measures: Temperature, pH, ORP (Chlorine), Salt, Conductivity, Battery
3. **ESPHome Configuration** (provided as reference)

### For Auxiliary Heating (Optional)
- Secondary smart switch controlling auxiliary heater

---

## Installation & Setup

### Step 1: Install Custom Component via HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Go to **HACS → Integrations → ⋮ (menu) → Custom repositories**
3. Add custom repository:
   - **Repository**: `https://github.com/lweberru/pool_controller`
   - **Category**: `Integration`
4. Click **Create**
5. Go to **HACS → Integrations** and search for **"Pool Controller"**
6. Click **Install**
7. Restart Home Assistant
8. Go to **Settings → Devices & Services → Create Automation → Pool Controller**

### Dashboard/Lovelace Card (separate repo)

The UI card is shipped in a separate HACS **Plugin** repository: https://github.com/lweberru/pool_controller_dashboard_frontend

1. Add that repo as custom repository in HACS (Category: Plugin)
2. Install; HACS will register the resource (URL `/hacsfiles/pool_controller_dashboard/main.js`).
3. Add the card `custom:pc-pool-controller` to your dashboard and use "Automatisch aus Instanz übernehmen" im Editor.

### Alternative: Manual Installation

If you prefer manual installation without HACS:

1. Copy the `custom_components/pool_controller` directory to your Home Assistant `custom_components/` folder
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Create Automation → Pool Controller**

### Step 2: Configuration Flow

The integration uses an interactive 5-step wizard:

#### Step 1: Basic Information
- **Name**: Display name for your pool (e.g., "Whirlpool Demo")
- **Main Switch**: Entity ID of main pump switch (required)
- **Water Volume**: Liters of water (used for pH/chlorine calculations)
- **Demo Mode**: Enable to test without actual devices

#### Step 2: Switches & Power Sensors
- **Main Switch**: Main pump switch entity (required)
- **Auxiliary Heating Switch**: Secondary heater (optional)
- **Power Sensors**: 
  - Main power sensor (kW) for heating calculations
  - Auxiliary power sensor (optional)

#### Step 3: Water Quality Sensors (Optional)
Configure only if using ESP32 + Blueriiot:
- **Water Temperature Sensor**: Current pool water temperature
- **Outdoor Temperature Sensor**: For frost protection logic
- **pH Sensor**: Water pH value (0-14)
- **Chlorine Sensor**: Redox/ORP value (mV)
- **Salt Sensor**: Salt concentration (g/L) - optional
- **Conductivity Sensor**: µS/cm - optional

#### Step 4: Calendar & Quiet Hours
- **Pool Calendar**: Calendar entity for operation schedule
- **Holiday Calendar**: Calendar for skipping noisy operations on holidays
- **Quiet Hours (Weekdays)**: Start/end times (e.g., 22:00 - 07:00)
- **Quiet Hours (Weekends)**: Start/end times

#### Step 5: PV Solar Integration
- **PV Surplus Sensor**: Entity measuring excess solar production (W)
- **PV ON Threshold**: Minimum W to enable heating via solar (default: 500W)
- **PV OFF Threshold**: Maximum W to disable heating (default: 100W)

---

## Configuration Options & Defaults

| Setting | Default | Range | Notes |
|---------|---------|-------|-------|
| Water Volume | 1000 | 100-10000 L | Used for pH/Chlorine dosing calculations |
| Filter Interval | 24 | 1-168 hours | Time between automatic filter cycles |
| Filter Duration | 30 | 5-480 min | How long each filter cycle runs |
| Bathing Duration | 60 | 5-480 min | Default bathing session length |
| Pause Duration | 30 | 5-480 min | Default pause duration |
| Frost Temp Threshold | 3°C | -5 to 10°C | Trigger frost protection |
| Heating Temp Target | 28°C | 20-40°C | Target water temperature |
| Quick Chlorine Duration | 5 | 1-30 min | Duration of chlorine boost |

All duration settings can be overridden per operation via **Services** (see below).

---

## Sensors & Entities

### Binary Sensors
| Entity | Description |
|--------|-------------|
| `binary_sensor.pool_is_we_holiday` | True if today is weekend or holiday |
| `binary_sensor.pool_frost_danger` | True when outdoor temp < 3°C |
| `binary_sensor.pool_is_quick_chlor` | Active quick chlorination |
| `binary_sensor.pool_is_paused` | Pool paused |
| `binary_sensor.pool_should_main_on` | Main pump should be running |
| `binary_sensor.pool_low_chlor` | Chlorine below recommended level |
| `binary_sensor.pool_ph_alert` | pH outside acceptable range |

### Sensors (Numeric & Status)
| Entity | Type | Description |
|--------|------|-------------|
| `sensor.pool_status` | Enum | Current state: `Normal`, `Paused`, `Frost Protection` |
| `sensor.pool_ph_value` | Float | Water pH (6.6-8.4 acceptable) |
| `sensor.pool_chlorine_level` | Float | Chlorine/ORP in mV |
| `sensor.pool_ph_minus_g` | Float | Recommended pH- dosage in grams |
| `sensor.pool_ph_plus_g` | Float | Recommended pH+ dosage in grams |
| `sensor.pool_chlorine_spoons` | Float | Recommended chlorine dosage in spoons |
| `sensor.pool_next_start_mins` | Integer | Minutes until next operation |
| `sensor.pool_next_event` | Timestamp | Next calendar event start |
| `sensor.pool_filter_cycles` | Integer | Total completed filter cycles |
| `sensor.pool_filter_end_time` | Timestamp | When current filter cycle ends |
| `sensor.pool_next_filter_mins` | Integer | Minutes until next filter cycle |
| `sensor.pool_pause_until` | Timestamp | When pause ends (if active) |
| `sensor.pool_bathing_until` | Timestamp | When bathing session ends |
| `sensor.pool_filter_until` | Timestamp | When filter cycle ends |

### Switches
| Entity | Description |
|--------|-------------|
| `switch.pool_main` | Main pump on/off |
| `switch.pool_aux` | Auxiliary heater on/off |
| `switch.pool_bathing` | Bathing mode on/off |

### Climate
| Entity | Description |
|--------|-------------|
| `climate.pool_heating` | Pool heater thermostat (target 28°C) |

---

## Buttons & Manual Controls

The integration provides 13 quick-action buttons:

### Chlorination
- `button.pool_quick_chlorine` - 5-minute chlorine boost

### Pause Controls
- `button.pool_pause_30` - Pause for 30 minutes
- `button.pool_pause_60` - Pause for 60 minutes
- `button.pool_pause_120` - Pause for 120 minutes
- `button.pool_pause_stop` - Cancel active pause

### Bathing Session Controls
- `button.pool_bath_30` - 30-minute bathing session
- `button.pool_bath_60` - 60-minute bathing session
- `button.pool_bath_120` - 120-minute bathing session
- `button.pool_bath_stop` - End active bathing session

### Filter Cycle Controls
- `button.pool_filter_30` - 30-minute filter cycle
- `button.pool_filter_60` - 60-minute filter cycle
- `button.pool_filter_120` - 120-minute filter cycle
- `button.pool_filter_stop` - Stop active filter cycle

---

## Services (Automations & Advanced)

All services support optional `duration_minutes` parameter for custom durations.

### Pause Management
```yaml
# Start pause (default 30 minutes)
service: pool_controller.start_pause
data:
  duration_minutes: 45  # optional

# Stop active pause
service: pool_controller.stop_pause
```

**Use Case**: Pause pool when guests are sleeping or during maintenance

### Bathing Sessions
```yaml
# Start bathing session (default 60 minutes)
service: pool_controller.start_bathing
data:
  duration_minutes: 120  # optional - great for extended family gatherings!

# End bathing session
service: pool_controller.stop_bathing
```

**Use Case**: Scheduled bath times via calendar or time automation

### Filter Cycles
```yaml
# Start filter cycle (default 30 minutes)
service: pool_controller.start_filter
data:
  duration_minutes: 60  # optional

# Stop filter cycle
service: pool_controller.stop_filter
```

**Use Case**: Manual filter triggers or extended filtration on high-use days

---

## Water Quality Monitoring (ESP32 + Blueriiot)

### Setting Up the ESP32

The integration works best with a dedicated ESP32 device running ESPHome that bridges your Blueriiot sensor to Home Assistant.

**Why this approach?**
- Blueriiot app functionality replaced with Home Assistant
- Real-time water metrics feed into Pool Controller decisions
- No subscription or proprietary app required

### Required Blueriiot Sensor
[**Blue Connect GO**](https://www.blueriiot.com/eu-en/products/blue-connect-go) - BLE wireless water quality monitor

**Measures:**
- 🌡️ Temperature (±0.5°C accuracy)
- 🧪 pH Level (0.1 pH accuracy)
- 💧 ORP / Chlorine (mV redox potential)
- 🧂 Salt Concentration (g/L)
- ⚡ Water Conductivity (µS/cm)
- 🔋 Battery Level

### ESP32 Configuration Example

See `esphome-blueriiot-example.yaml` in the repository root for a complete working example.

**Key configuration sections:**

```yaml
substitutions:
  name: esp32-5
  roomname: Garten
  staticip: 192.168.1.205
  blueriiot1_mac: '00:A0:50:C7:46:C9'  # Your Blueriiot device MAC
  blueriiot1_name_prefix: 'whirlpool'
  blueriiot1_id_prefix: 'p2'

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: esp-idf
    version: recommended
  flash_size: 16MB
  variant: ESP32S3

# ... rest of config for BLE scanning, display, sensors, etc.
```

**Installation Steps:**
1. Update substitutions (MAC address, IP, etc.)
2. Flash ESPHome to your ESP32 via USB
3. Connect to Home Assistant via ESPHome add-on
4. Configure Pool Controller to use the water quality sensors

### Sensor Values in Pool Controller
Once configured, the integration automatically:
- ✅ Recommends pH adjustments (pH-, pH+)
- ✅ Recommends chlorine dosing
- ✅ Flags low chlorine (ORP < 400mV)
- ✅ Flags pH out of range
- ✅ Displays all metrics in sensors

---

## Advanced Features Explained

### Filtration Logic
- **Auto-filtering**: Runs on configurable interval (default: daily)
- **Smart scheduling**: Respects quiet hours and frost danger
- **Manual override**: Start/stop via buttons or services
- **Duration control**: Adjustable per cycle

### Temperature Control & Water Volume Calculations

The **water volume** setting is critical for two automated calculations:

#### 1. Heating Time Calculation

**Formula:**
```
Time (minutes) = (Water Volume (L) × 1.16 × ΔT (°C)) / Power (W) × 60

Where:
- 1.16 = Specific heat capacity of water (Wh/L/°C)
- ΔT = Target temperature - Current water temperature
- Power = Heater power consumption (from power sensor or 3000W default)
```

**Example:**
- Pool: 1000 L
- Current temp: 20°C, Target: 38°C → ΔT = 18°C
- Heater: 3000W (3kW)

```
Time = (1000 × 1.16 × 18) / 3000 × 60 = 418 minutes ≈ 7 hours
```

**Usage:** This calculation determines when to **pre-heat** before calendar events. If your pool calendar shows "Bathing at 18:00" and heating takes 7 hours, the pump automatically starts at 11:00.

#### 2. pH Adjustment Dosage

**Formulas with Tolerance Range:**
```
Target pH: 7.2
OK Range: 7.0 - 7.4 (no dosing needed)

pH- (Senker) in grams = (Current pH - 7.2) × 100 × Volume (m³)  [only when pH > 7.4]
pH+ (Heber) in grams = (7.2 - Current pH) × 100 × Volume (m³)  [only when pH < 7.0]
```

**Examples:**
- Pool: 1000 L (1 m³)

**Case 1 - pH too high:**
- Measured pH: 7.8
- `pH- needed = (7.8 - 7.2) × 100 × 1 = 60 grams`

**Case 2 - pH too low:**
- Measured pH: 6.8
- `pH+ needed = (7.2 - 6.8) × 100 × 1 = 40 grams`

**Case 3 - pH in OK range:**
- Measured pH: 7.15
- `No dosing needed (within 7.0-7.4 tolerance)`

#### Chlorine Dosing Calculation

**Formula** (basis: 1000L reference volume):
```
Target: 700 mV (ideal chlorine level)
Per 100 mV below 700 → +0.25 spoons (for 1000L)
Rounded to 0.25 spoon increments

chlorine_spoons = round((700 - chlor_mV) / 100) / 4 × (volume_L / 1000)
```

**Example:**
- Water volume: 1000L  
- Current: 400 mV  
- Calculation: `(700 - 400) / 100 = 3` → `3 / 4 = 0.75 spoons`

**For other volumes:**
- 1500L pool at 400 mV: `0.75 × 1.5 = 1.13 spoons`
- 500L pool at 400 mV: `0.75 × 0.5 = 0.38 spoons`

**Usage:** The integration displays recommended dosages in sensors:
- `sensor.pool_ph_minus_g` - Shows grams of pH- to add
- `sensor.pool_ph_plus_g` - Shows grams of pH+ to add
- `sensor.pool_chlorine_spoons` - Shows chlorine dosage in measuring spoons

**Important Notes:**
- ⚠️ **Accurate volume is essential** - A 20% error in volume translates to 20% error in dosing recommendations
- 💡 Measure your pool volume carefully (length × width × average depth for rectangular pools)
- 🧪 Formulas assume standard pool chemistry products (strength may vary by brand)
- ⚡ Chlorine formula calibrated for typical granular chlorine dosing (adjust if using liquid/tablet forms)
- 🔧 For irregular shapes, fill from empty and use water meter reading

---

### Temperature Control (Extended)

**Heating enabled when:**
- ✅ Pool not paused
- ✅ Not in frost protection mode
- ✅ Calendar event active (optional)
- ✅ PV solar production above ON threshold (if configured)

### PV Solar Optimization
When connected to solar:
- Heating only engages if excess PV production > ON threshold
- Heating stops when excess drops below OFF threshold
- Maximizes self-consumption of solar energy
- Example: Enable heating only when producing >500W surplus

### Quiet Hours
Prevents noisy operations during sensitive times:
- **Weekday quiet hours**: 22:00-07:00 (no pump)
- **Weekend quiet hours**: 23:00-08:00 (no pump)
- **Holiday bypass**: No operations during calendar holidays
- Overrideable via manual buttons

### Frost Protection
When outdoor temperature drops below 3°C:
- ⚠️ Activates automatically
- ⚠️ Keeps main pump running
- ⚠️ Overrides quiet hours
- ⚠️ Prevents water freezing in pipes

---

## Optional Features

### Auxiliary Heating
If you've added an extra heater (resistive, heat pump, etc.):
1. Configure a secondary smart switch entity during setup
2. Switch appears as `switch.pool_aux`
3. Controlled independently via automation or manual button

### Salt Water Chlorination
If your pool uses salt chlorination:
- Configure salt sensor from Blueriiot
- Integration tracks salt levels
- Helps maintain proper electrolysis conditions

---

## Common Automations

### Example 1: Heat pool before weekend bathing
```yaml
automation:
  - alias: "Heat pool for weekend bathing"
    trigger:
      time: "14:00"
    condition:
      - condition: time
        weekday: [fri]
    action:
      - service: pool_controller.start_bathing
        data:
          duration_minutes: 180  # 3-hour session
```

### Example 2: Emergency pause on low chlorine
```yaml
automation:
  - alias: "Pause on low chlorine alert"
    trigger:
      entity_id: binary_sensor.pool_low_chlor
      to: "on"
    action:
      - service: pool_controller.start_pause
        data:
          duration_minutes: 60
      - notify.send_message:
          message: "Pool paused - chlorine too low!"
```

### Example 3: Extended filtering on hot days
```yaml
automation:
  - alias: "Extra filter on high temp days"
    trigger:
      numeric_state:
        entity_id: sensor.pool_ph_value
        above: 30  # Above 30°C
    action:
      - service: pool_controller.start_filter
        data:
          duration_minutes: 120  # Extra 2 hours
```

### Example 4: Daily maintenance at 2 AM
```yaml
automation:
  - alias: "Daily filter cycle"
    trigger:
      time: "02:00"
    condition:
      - condition: state
        entity_id: binary_sensor.pool_frost_danger
        state: "off"
    action:
      - service: pool_controller.start_filter
        data:
          duration_minutes: 45
```

---

## Status Sensors & Debugging

### Pool Status States
| State | Meaning |
|-------|---------|
| `Normal` | Pool operating normally |
| `Paused` | Pause timer active |
| `Frost Protection` | Frost danger - protection active |

### Useful Diagnostic Sensors
- `sensor.pool_next_start_mins` - When next operation starts
- `sensor.pool_next_event` - Next calendar event
- `binary_sensor.pool_should_main_on` - What *should* be running
- `sensor.pool_filter_cycles` - Maintenance indicator

Enable debug logging in Home Assistant:
```yaml
logger:
  logs:
    custom_components.pool_controller: debug
```

---

## Language Support

The integration includes full translations for:
- 🇩🇪 **Deutsch** (German)
- 🇬🇧 **English**
- 🇪🇸 **Español** (Spanish)
- 🇫🇷 **Français** (French)

All entity names, buttons, and configuration labels are translated automatically based on your Home Assistant language setting.

---

## Troubleshooting

### "Unknown entity" errors during setup
- Verify sensor entity IDs exist in your HA instance
- Optional sensors can be left empty if not configured
- Check entity IDs spelling (case-sensitive)

### Pool not turning on
- Check `binary_sensor.pool_should_main_on` state
- Review quiet hours and calendar events
- Verify frost protection not active
- Check `sensor.pool_status` for current state

### Heating not working
- Verify power sensor is configured and reporting
- Check heating thermostat target (default 28°C)
- Ensure calendar event is active (if required)
- Review PV thresholds if solar-dependent

### Water quality sensor not updating
- Confirm Blueriiot sensor in range and powered
- Check ESP32 WiFi connection and ESPHome status
- Verify BLE connection in ESP32 logs
- Try pressing "Start BLE Scan" button on ESP32

---

## Development & Contributing

This integration is open-source. Contributions are welcome!

- **GitHub**: [lweberru/pool_controller](https://github.com/lweberru/pool_controller)
- **Issues**: Report bugs or request features
- **Pull Requests**: Submit improvements

---

## License

MIT License - See LICENSE file in repository

---

## Support

For issues, questions, or feature requests:
1. Check existing GitHub issues
2. Review Home Assistant logs (`Settings → System → Logs`)
3. Open a new GitHub issue with:
   - Pool Controller version
   - Home Assistant version
   - Integration setup details
   - Relevant logs/error messages

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.

---

**Enjoy automated pool management!** 🏊‍♂️
