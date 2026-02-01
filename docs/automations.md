# Common Automations

[← Back to README](../README.md)

## Example 1: Heat pool before weekend bathing

```yaml
automation:
  - alias: "Heat pool for weekend bathing"
    trigger:
      - platform: time
        at: "14:00"
    condition:
      - condition: time
        weekday: [fri]
    action:
      - action: pool_controller.start_bathing
        data:
          target:
            entity_id: climate.my_pool
          duration_minutes: 180  # 3-hour session
```

## Example 2: Emergency pause on low chlorine

```yaml
automation:
  - alias: "Pause on low chlorine alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_pool_low_chlor
        to: "on"
    action:
      - action: pool_controller.start_pause
        data:
          target:
            entity_id: climate.my_pool
          duration_minutes: 60
      - action: notify.send_message
          message: "Pool paused - chlorine too low!"
```

## Example 3: Extended filtering on hot days

```yaml
automation:
  - alias: "Extra filter on high temp days"
    trigger:
      - platform: numeric_state
        entity_id: climate.my_pool
        attribute: current_temperature
        above: 30  # Above 30°C
    action:
      - action: pool_controller.start_filter
        data:
          target:
            entity_id: climate.my_pool
          duration_minutes: 120  # Extra 2 hours
```

## Example 4: Daily maintenance at 2 AM

```yaml
automation:
  - alias: "Daily filter cycle"
    trigger:
      - platform: time
        at: "02:00"
    condition:
      - condition: state
        entity_id: binary_sensor.my_pool_frost_danger
        state: "off"
    action:
      - action: pool_controller.start_filter
        data:
          target:
            entity_id: climate.my_pool
          duration_minutes: 45
```
