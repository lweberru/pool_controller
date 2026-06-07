# Typische Automationen

[English](../automations.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

## Beispiel 1: Pool vor dem Wochenendbaden aufheizen

```yaml
automation:
  - alias: "Pool fürs Wochenendbaden aufheizen"
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
          duration_minutes: 180
```

## Beispiel 2: Notfallpause bei zu wenig Chlor

```yaml
automation:
  - alias: "Pause bei Chlorwarnung"
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
        data:
          message: "Pool pausiert - Chlor zu niedrig!"
```

## Beispiel 3: Längere Filterung an heißen Tagen

```yaml
automation:
  - alias: "Extra-Filterung an heißen Tagen"
    trigger:
      - platform: numeric_state
        entity_id: climate.my_pool
        attribute: current_temperature
        above: 30
    action:
      - action: pool_controller.start_filter
        data:
          target:
            entity_id: climate.my_pool
          duration_minutes: 120
```

## Beispiel 4: Tägliche Filterung um 2 Uhr nachts

```yaml
automation:
  - alias: "Täglicher Filterzyklus"
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

## Beispiel 5: Away-Modus aktivieren, wenn niemand zu Hause ist

```yaml
automation:
  - alias: "Pool auf Away wenn niemand da ist"
    trigger:
      - platform: state
        entity_id: group.family
        to: "not_home"
    action:
      - action: pool_controller.start_away
        data:
          target:
            entity_id: climate.my_pool

  - alias: "Pool zurück auf normal wenn jemand heimkommt"
    trigger:
      - platform: state
        entity_id: group.family
        to: "home"
    action:
      - action: pool_controller.stop_away
        data:
          target:
            entity_id: climate.my_pool
```