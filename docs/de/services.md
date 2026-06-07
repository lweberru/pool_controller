# Aktionen

[English](../services.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

Alle Aktionen unterstützen optional den Parameter `duration_minutes`, wenn du von der Standarddauer abweichen willst.

Wenn du mehrere pool_controller-Instanzen hast, verwende das neue **target**-Schema:
- `target.entity_id` für die Climate-Entität des Pools
- oder `target.device_id` für das von der Integration angelegte Gerät

Unterstützte Formen:
- `target.entity_id` als String oder Liste
- `target.device_id` als String oder Liste
- die alten Top-Level-Felder `entity_id` und `device_id` werden weiterhin akzeptiert

Auflösungsreihenfolge:
1. passende `entity_id`, bevorzugt
2. passende `device_id`
3. Fallback nur dann, wenn exakt eine einzige pool_controller-Instanz existiert

## Pause-Verwaltung

```yaml
# Pause starten, Standard 60 Minuten
action: pool_controller.start_pause
data:
  target:
    entity_id: climate.my_pool
  duration_minutes: 45

# Aktive Pause beenden
action: pool_controller.stop_pause
data:
  target:
    entity_id: climate.my_pool
```

**Typischer Einsatz:** Pool pausieren, wenn Gäste schlafen oder Wartung ansteht.

## Badesitzungen

```yaml
# Baden starten, Standard 60 Minuten
action: pool_controller.start_bathing
data:
  target:
    entity_id: climate.my_pool
  duration_minutes: 120

# Baden beenden
action: pool_controller.stop_bathing
data:
  target:
    entity_id: climate.my_pool
```

**Typischer Einsatz:** Geplante Badezeiten über Kalender oder Zeit-Automationen.

## Filterzyklen

```yaml
# Filterung starten, Standard 30 Minuten
action: pool_controller.start_filter
data:
  target:
    entity_id: climate.my_pool
  duration_minutes: 60

# Filterung beenden
action: pool_controller.stop_filter
data:
  target:
    entity_id: climate.my_pool
```

## Chlorung Schnellchlorung

```yaml
# Schnellchlorung starten, Standard 5 Minuten
action: pool_controller.start_chlorine
data:
  target:
    entity_id: climate.my_pool
  duration_minutes: 5

# Schnellchlorung beenden
action: pool_controller.stop_chlorine
data:
  target:
    entity_id: climate.my_pool
```

**Typischer Einsatz:** Manuelle Chlorstoßphase oder verlängerte Aufbereitung nach intensiver Nutzung.

## Wartungsmodus

```yaml
# Wartungsmodus aktivieren, harter Lockout
action: pool_controller.start_maintenance
data:
  target:
    entity_id: climate.my_pool

# Wartungsmodus deaktivieren
action: pool_controller.stop_maintenance
data:
  target:
    entity_id: climate.my_pool
```

## Away-Modus

```yaml
# Away-Modus aktivieren, reduziert Aktivität und setzt Away-Temperatur
action: pool_controller.start_away
data:
  target:
    entity_id: climate.my_pool

# Away-Modus deaktivieren
action: pool_controller.stop_away
data:
  target:
    entity_id: climate.my_pool
```

## Stromsparmodus

```yaml
# Stromsparmodus aktivieren, PV-priorisierter Betrieb
action: pool_controller.start_power_saving
data:
  target:
    entity_id: climate.my_pool

# Stromsparmodus deaktivieren
action: pool_controller.stop_power_saving
data:
  target:
    entity_id: climate.my_pool
```

**Verhalten:**
- Frostschutz und sicherheitsrelevante Logik bleiben aktiv.
- Betrieb wird bevorzugt in Phasen mit ausreichender PV-Leistung gelegt.
- Automatische Filterläufe können verschoben werden und werden ab der konfigurierten Deadline-Stunde erzwungen.
- Die Verfügbarkeit hängt von Sensoren ab; der Modus wird verborgen oder deaktiviert, wenn notwendige Signale fehlen.

## Alternative: target über device_id

```yaml
action: pool_controller.start_bathing
data:
  target:
    device_id: 1234567890abcdef
  duration_minutes: 90
```