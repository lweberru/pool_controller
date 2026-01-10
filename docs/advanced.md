# Advanced Features

[← Back to README](../README.md)

## Filtration Logic
- **Auto-filtering**: Runs on configurable interval
- **Smart scheduling**: Respects quiet hours and frost danger
- **Manual override**: Start/stop via buttons or services
- **Duration control**: Adjustable per cycle

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
