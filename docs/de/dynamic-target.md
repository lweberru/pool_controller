# Dynamische Zieltemperatur

[English](../dynamic-target.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

## Ziel

Die dynamische Zieltemperatur passt den effektiven Sollwert rund um deine konfigurierte Basis-Zieltemperatur an.

- Basis-Sollwert bleibt die Nutzerabsicht.
- Ein dynamischer Offset wird aus Saison und Wetter berechnet.
- Der effektive Sollwert wird im Regelkreis für Heizentscheidungen verwendet.

Laufzeitformel:

```text
target_effective = target_base + offset_total
offset_total = clamp(offset_season + offset_weather, min_offset, max_offset)
```

Das Feature ist bewusst ausgewogen und standardmäßig deaktiviert:

- `enable_dynamic_target = false`
- Bei deaktiviertem Feature bleibt das bisherige Verhalten erhalten.

## Laufzeitmodell

### 1. Saisonprofil

Über das Jahr wird eine glatte Interpolation zwischen vier Ankerwerten genutzt:

- Winter-Offset
- Frühlings-Offset
- Sommer-Offset
- Herbst-Offset

Defaults:

- Winter: `+4.0°C`
- Frühling: `+2.0°C`
- Sommer: `-4.5°C`
- Herbst: `+1.0°C`
- Gesamtgrenzen: `[-6.5°C, +5.0°C]`

### 2. Wetteranteil

Wenn eine Wetter-Entity gesetzt ist, wird ein zusätzlicher wetterbasierter Korrekturwert berechnet.
Der Wetteranteil wird über `dynamic_target_weather_max_offset` begrenzt (Default `±3.0°C`).

Unterstützte gewichtete Eingänge:

- Temperatur
- Gefühlt-Temperatur
- Wind
- UV
- Wolkenanteil
- Forecast-Anteil

Default-Gewichte:

- Temperatur: `0.55`
- Gefühlt: `0.30`
- Wind: `0.15`
- UV: `0.10`
- Wolken: `0.10`
- Forecast: `0.10`

### 3. Glättung und Schrittbegrenzung

Zur Vermeidung harter Sprünge:

- EMA-Glättung mit `dynamic_target_ema_alpha` (Default `0.20`)
- Änderungsbegrenzung mit `dynamic_target_max_step_per_hour` (Default `1.0°C/h`)

Damit bleiben UI und Aktorverhalten auch bei unruhigen Wetterdaten stabil.

## Konfiguration

Konfigurierbar im Optionsflow unter dem Bereich Dynamische Zieltemperatur.

Wichtige Optionen:

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

## Exponierte Sensoren

Die Integration stellt Diagnosewerte bereit:

- `sensor.<pool>_target_temperature_base`
- `sensor.<pool>_target_temperature_effective`
- `sensor.<pool>_target_offset`
- `sensor.<pool>_saison_offset`
- `sensor.<pool>_wetter_offset`
- `sensor.<pool>_dynamic_target_profile`

Diese Werte werden in der Dashboard-Karte genutzt und helfen bei der Fehlersuche.

## Zusammenspiel mit Heizung und Wasserchemie

- Heizung/Vorheizen arbeitet mit `target_temperature_effective`.
- Die Gültigkeit von Chemie-Empfehlungen hängt nicht direkt von der dynamischen Zieltemperatur ab.
- Nach Neustarts kann Chemie dennoch in `measure_first` bleiben, bis stabile Samples wieder ausreichend vorhanden sind.

## Empfohlene Tuning-Strategie

1. Mit Defaults starten und Feature aktivieren.
2. `target_offset` und `target_temperature_effective` für 3 bis 7 Tage beobachten.
3. Zuerst Saisonanker anpassen.
4. Danach, falls nötig, Wettergewichte anpassen.
5. Schrittgrenze konservativ lassen (`<= 1.0°C/h`), außer bei sehr stabiler Wetterquelle.

## Troubleshooting

Wenn der Sollwert zu unruhig wirkt:

- Wetter-Entity auf Qualität und Update-Frequenz prüfen.
- Wettergewichte reduzieren.
- EMA-Alpha senken.
- Maximalen Schritt pro Stunde senken.

Wenn das Verhalten exakt wie früher sein soll:

- Dynamische Zieltemperatur deaktivieren (`enable_dynamic_target = false`).
