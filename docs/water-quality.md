# Water Quality Monitoring & Disinfection

[← Back to README](../README.md)

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

### Sensor Values in Pool Controller

Once configured, the integration automatically:
- ✅ Recommends pH adjustments (pH-, pH+)
- ✅ Recommends chlorine dosing
- ✅ Monitors TDS and recommends water changes
- ✅ Flags low chlorine (ORP < 400mV)
- ✅ Flags pH out of range
- ✅ Displays all metrics in sensors

For a consolidated view of all **maintenance recommendation sensors** and the calculation details, see
[Maintenance & Recommendations](maintenance.md).

## pH Adjustment Dosage

**Formulas with Tolerance Range:**

```
Target pH: 7.2
OK Range: 7.0 - 7.4 (no dosing needed)

pH- (Senker) in grams = (Current pH - 7.2) × 100 × Volume (m³)  [only when pH > 7.4]
pH+ (Heber) in grams = (7.2 - Current pH) × 100 × Volume (m³)  [only when pH < 7.0]
```

## Chlorine Dosing Calculation

**Formula** (basis: 1000L reference volume):

```
Target: 700 mV (ideal chlorine level)
Per 100 mV below 700 → +0.25 spoons (for 1000L)
Rounded to 0.25 spoon increments

chlorine_spoons = round((700 - chlor_mV) / 100) / 4 × (volume_L / 1000)
```

## Sanitizer mode (chlorine / saltwater / mixed)

Pool Controller can run in different disinfection modes:

- `chlorine`: classic chlorine-based pool/spa; water-quality interpretation uses the raw (derived) TDS.
- `saltwater`: salt chlorinator systems; conductivity/TDS is dominated by salt, so Pool Controller computes an **effective TDS** value (approx. non-salt dissolved solids).
- `mixed`: saltwater + chlorine dosing; also uses **effective TDS**.

The selected mode is exposed as:
- `sensor.<pool>_sanitizer_mode`

If you upgrade from an older version: the legacy boolean `enable_saltwater` is still recognized for backward compatibility, but the preferred configuration is `sanitizer_mode`.

## TDS (Total Dissolved Solids) & Water Change Recommendation

If you provide a **conductivity sensor** (typically from Blueriiot), Pool Controller derives **TDS in ppm** and recommends how much water to replace to reduce TDS back toward a target level.

### 1) Conductivity → TDS conversion

The integration expects conductivity in **μS/cm** and converts it to TDS (ppm) using a standard factor:

```
tds_ppm = round(conductivity_uS_cm × 0.64)
```

This value is exposed as:
- `sensor.<pool>_tds_val` (ppm)

### 1b) Effective TDS (saltwater/mixed)

In `saltwater` / `mixed` mode, raw conductivity/TDS is mostly reflecting the intended salt level.
To avoid permanently showing “too high”, Pool Controller computes:

```
salt_baseline_ppm = target_salt_g_l × 1000
tds_effective = max(0, tds_val - salt_baseline_ppm)
```

This value is exposed as:
- `sensor.<pool>_tds_effective` (ppm)

All status/alerting and water-change recommendations use **effective TDS** when available (otherwise they fall back to raw `tds_val`).

### 2) TDS status and alerting

Based on the ppm value used for maintenance (effective TDS when available), the integration sets a status and a binary alert:

- `sensor.<pool>_tds_status` (enum): `optimal`, `good`, `high`, `critical`, `urgent`
- `binary_sensor.<pool>_tds_high`: `on` when water change is needed

Current backend thresholds:

- `< 1500 ppm` → `optimal`
- `< 2000 ppm` → `good`
- `< 2500 ppm` → `high` (sets `tds_high`)
- `< 3000 ppm` → `critical` (sets `tds_high`)
- `≥ 3000 ppm` → `urgent` (sets `tds_high`)

### 3) Recommended water change (liters + percent)

To estimate how much water needs to be replaced to bring TDS down, the integration uses a simple dilution model with a target TDS:

- Target TDS: `1200 ppm`

Formula (uses the maintenance TDS value: effective when available, otherwise raw):

```
water_change_liters = round(volume_L × (tds_maint_ppm - target_ppm) / tds_maint_ppm)   [only when tds_maint_ppm > target_ppm]
water_change_percent = round((water_change_liters / volume_L) × 100)
```

These recommendations are exposed as:
- `sensor.<pool>_tds_water_change_liters` (L)
- `sensor.<pool>_tds_water_change_percent` (%)
