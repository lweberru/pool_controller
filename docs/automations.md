# Common Automations

[← Back to README](../README.md)

## Example 1: Heat pool before weekend bathing

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

## Example 2: Emergency pause on low chlorine

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

## Example 3: Extended filtering on hot days

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

## Example 4: Daily maintenance at 2 AM

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
