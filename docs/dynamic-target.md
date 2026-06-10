# Dynamic Target Temperature

**English** | [Deutsch](de/dynamic-target.md)

[← Back to README](../README.md)

## Goal

The dynamic target feature adjusts the effective setpoint around your configured base temperature.

- Base target remains the user intent.
- Dynamic offset is computed from season and weather.
- Effective target is used by the control loop for heating decisions.

Formula used in runtime:

```text
target_effective = target_base + offset_total
offset_total = clamp(offset_season + offset_weather, min_offset, max_offset)
```

The implementation is intentionally conservative and disabled by default:

- `enable_dynamic_target = false`
- Behavior is unchanged when disabled.

## Runtime Model

### 1. Seasonal profile

A smooth annual interpolation is applied between four anchor offsets:

- Winter offset
- Spring offset
- Summer offset
- Autumn offset

Defaults:

- Winter: `+4.0°C`
- Spring: `+2.0°C`
- Summer: `-4.5°C`
- Autumn: `+1.0°C`
- Total clamp: `[-4.5°C, +4.0°C]`

### 2. Weather contribution

If a weather entity is configured, a weather-based correction is added.
The contribution is limited by `dynamic_target_weather_max_offset` (default `±2.0°C`).

Supported weighted inputs:

- Temperature
- Feels-like temperature
- Wind
- UV
- Cloud coverage
- Forecast contribution

Default weights:

- Temp: `0.45`
- Feels-like: `0.20`
- Wind: `0.15`
- UV: `0.10`
- Cloud: `0.10`
- Forecast: `0.10`

### 3. Smoothing and step limit

To avoid aggressive jumps:

- EMA smoothing with `dynamic_target_ema_alpha` (default `0.12`)
- Rate limit with `dynamic_target_max_step_per_hour` (default `1.0°C/h`)

This keeps UI and actuator behavior stable even with noisy weather feeds.

## Configuration

Set in options flow under the dynamic target section.

Important options:

- `enable_dynamic_target`
- `dynamic_target_weather_entity`
- `dynamic_target_winter_offset`
- `dynamic_target_spring_offset`
- `dynamic_target_summer_offset`
- `dynamic_target_autumn_offset`
- `dynamic_target_min_offset`
- `dynamic_target_max_offset`
- `dynamic_target_weather_max_offset`
- `dynamic_target_weather_weight_temp`
- `dynamic_target_weather_weight_feels_like`
- `dynamic_target_weather_weight_wind`
- `dynamic_target_weather_weight_uv`
- `dynamic_target_weather_weight_cloud`
- `dynamic_target_weather_weight_forecast`
- `dynamic_target_ema_alpha`
- `dynamic_target_max_step_per_hour`

## Exposed Sensors

The integration publishes diagnostics for transparency:

- `sensor.<pool>_target_temperature_base`
- `sensor.<pool>_target_temperature_effective`
- `sensor.<pool>_target_offset`
- `sensor.<pool>_saison_offset`
- `sensor.<pool>_wetter_offset`
- `sensor.<pool>_dynamic_target_profile`

These values are used by the dashboard card and helpful for troubleshooting.

## Interaction with Heating and Chemistry

- Heating/preheat uses `target_temperature_effective`.
- Water chemistry recommendation validity does not directly depend on dynamic target.
- Chemistry actions can still remain in `measure_first` after restart when stable sample conditions are not yet fulfilled.

## Recommended Tuning Strategy

1. Start with defaults and enable the feature.
2. Observe `target_offset` and `target_temperature_effective` for 3 to 7 days.
3. Adjust seasonal anchors first.
4. Only then adjust weather weights.
5. Keep max step conservative (`<= 1.0°C/h`) unless you have a very stable weather source.

## Troubleshooting

If target looks unstable:

- Check weather entity quality and update frequency.
- Reduce weather weights.
- Lower EMA alpha.
- Lower max step/hour.

If behavior should match old setup exactly:

- Disable dynamic target (`enable_dynamic_target = false`).
