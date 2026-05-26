# Pool Controller - Advanced Home Assistant Integration

![Latest Version](https://img.shields.io/github/v/release/lweberru/pool_controller)
![License](https://img.shields.io/badge/license-MIT-blue)

> **Fork notice / Hinweis:** This is a fork of [lweberru/pool_controller](https://github.com/lweberru/pool_controller) with additional fixes around config-flow defaults, pump-switch fallback, and one-shot migration for legacy entity IDs. See the [CHANGELOG](CHANGELOG.md) for details.

## Overview

**Pool Controller** is a Home Assistant custom integration designed to manage and automate your spa or pool when the device lacks built-in smart capabilities.

If your spa/pool is connected to a simple smart switch (on/off only), you lose access to important automation features (filtration cycles, temperature control, frost protection, water quality monitoring). **Pool Controller** brings these back and adds additional comfort/efficiency features.

## Dashboard Card Preview

![Pool Controller Dashboard Card 1](card_example_1.png)
![Pool Controller Dashboard Card 2](card_example_2.png)

> The dashboard card shown above is available as a separate HACS plugin: [lweberru/pool_controller_dashboard_frontend](https://github.com/lweberru/pool_controller_dashboard_frontend). It depends on [`apexcharts-card`](https://github.com/RomRider/apexcharts-card) — install that first, otherwise the PV/cost charts render as "Configuration error".

## Documentation

This repository's documentation has been split into chapters for easier navigation:

- [Installation & Setup](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Sensors, Entities & Controls](docs/entities.md)
- [Costs & Electricity Prices](docs/costs.md)
- [Services (Automations & Advanced)](docs/services.md)
- [Water Quality Monitoring & Disinfection](docs/water-quality.md)
- [Advanced Features](docs/advanced.md)
- [Common Automations](docs/automations.md)
- [Troubleshooting](docs/troubleshooting.md)

## Contributing

Development rules and release workflow (HACS via GitHub Releases): see [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

# 🇩🇪 Deutsche Anleitung

## Was diese Integration macht

**Pool Controller** ist eine Custom Integration für Home Assistant, die deinen Pool oder Whirlpool intelligent steuert — auch wenn die Pumpe selbst nur über eine simple smarte Steckdose (an/aus) geschaltet wird.

Die Integration übernimmt die komplette Logik, die ein klassischer Pool-Controller hätte:

- **Automatische Filterzyklen** über den Tag verteilt (z.B. 2× 50 min bei 7 000-L-Pool und 8 m³/h-Pumpe)
- **PV-Überschussnutzung** — Pumpe läuft, wenn Solar-Überschuss da ist, statt Netzstrom zu ziehen
- **Power-Saving / Stromsparen** — verschiebt Filterläufe ins PV-Fenster, sofern möglich
- **Quiet-Hours / Ruhezeiten** — keine Pumpenstarts nachts (Nachbarn freuen sich)
- **Frostschutz** im Winter (zyklisches Anlaufen unter Schwellentemperatur)
- **Thermostat-Logik** mit Zusatzheizung (optional)
- **Wasserqualitäts-Überwachung**: pH, Chlor (ORP), Salz, TDS — sofern Sensoren vorhanden
- **Stoßchlorung**, **Pause**, **Bade-Modus** als Buttons / Services
- **Kosten-Tracking** (Brutto/Netto mit PV-Abzug, Einspeisevergütung)
- **Kalender-Integration** für geplante Bade-Sessions (z.B. Whirlpool vor dem Eintauchen vorwärmen lassen)

## Schnellstart

### 1. Installation via HACS (Custom Repository)

1. **HACS → ⋮ → Custom repositories**
2. Repository-URL: dieses Repo (Fork-URL), Category: **Integration** → Add
3. HACS → Integrations → **Advanced Pool Controller** → Download
4. Home Assistant neu starten

### 2. Frontend-Card (optional, aber empfohlen)

Die Dashboard-Card ist ein separates Repo:
- **HACS → Custom repositories**: `https://github.com/lweberru/pool_controller_dashboard_frontend` → Category: **Dashboard**
- Download → HA-Frontend einmal hart neu laden (Strg+Shift+R)

⚠️ Die Card nutzt intern **`apexcharts-card`** für die PV-/Kosten-Diagramme. Wenn du den `apexcharts-card` nicht installiert hast, zeigt sie "Konfigurationsfehler". Über HACS → Frontend → "apexcharts-card" (von RomRider) installieren.

### 3. Integration einrichten

**Settings → Devices & Services → Add Integration → "Pool Controller"**

Du wirst durch einen mehrstufigen Wizard geführt (Basis, Schalter, Wasserqualität, Klima, Frost, Kalender, Filter, PV, Kosten). Felder, die du nicht kennst oder nicht hast: **leer lassen** — die Integration nutzt dann sinnvolle Defaults oder schaltet das Feature einfach ab.

Pflichtfelder sind nur:
- **Hauptschalter** (smarte Steckdose der Pool-Pumpe)
- **Wassertemperatur-Sensor**

Alles andere ist optional.

## Empfohlene Werte (Faustregeln)

### Filter-Zyklen

Faustregel: **Pool-Volumen 2× pro Tag umwälzen** (3× bei viel Nutzung oder Hitze).

| Pool-Volumen | Pumpe | Empfehlung |
|---|---|---|
| 7 000 L | 8 m³/h | `filter_interval_minutes: 720`, `filter_minutes: 50` |
| 10 000 L | 8 m³/h | `filter_interval_minutes: 720`, `filter_minutes: 75` |
| 30 000 L | 10 m³/h | `filter_interval_minutes: 480`, `filter_minutes: 100` |

`filter_minutes` zu hoch wählen schadet nicht der Chemie, aber kostet Strom und Pumpenstandzeit.

### Quiet-Hours

`quiet_time_start: "22:00"` / `quiet_time_end: "08:00"` ist eine vernünftige Standardannahme — Nachbarn nicht stören, PV-Nutzung am Morgen nicht zu früh blockieren.

### PV-Optimierung

- **`pv_on_threshold`** ≈ Pumpenleistung + 150 W Puffer (typisch 500–800 W für 7–10 m³/h-Pumpen)
- **`pv_off_threshold`** ≈ halber `pv_on_threshold` — verhindert Flackern
- **`pv_min_run_minutes: 15`** — Pumpe soll nicht im 2-Minuten-Takt ein/aus
- **`power_saving_filter_deadline_hour: 19`** — bis 19 Uhr darf PV-getriggert noch ein Filter starten; danach wartet die Integration auf den nächsten regulären Slot

### Wasserchemie-Sensoren (optional, sehr empfohlen)

Die Integration kann **pH**, **Chlor (ORP)**, **Salz** und **TDS** auswerten. Wenn du keine entsprechenden Sensoren hast: Felder leer lassen.

DIY-Empfehlung (Hobby-Budget ~70–140 €):

- **pH**: DFRobot Gravity Analog pH Sensor V2 (SEN0169-V2) ~55 €
- **Chlor**: DFRobot Gravity Analog ORP Sensor Pro Kit (SEN0165) ~85 €
- **ESP32** (~12 €) mit ESPHome → liefert beide Werte als HA-Sensor
- Bei gleichzeitigem Einsatz von pH **und** ORP im selben Wasser zusätzlich: DFRobot Isolated Signal Conditioner (DFR0521, ~25 €) — verhindert Cross-Talk zwischen den Elektroden

Fertig-Lösungen (Plug & Play, teurer, oft cloud-abhängig):
- **Blue Connect Go** (Bluetooth, Schwimmkörper) ~250 €
- **iopool EcO** ~200 €

## Kalender-Verwendung

Wenn ein **Pool-Kalender** konfiguriert ist (eigener Local Calendar oder bestehende `calendar.*`-Entity), interpretiert die Integration **jedes Event** als geplante **Bade-Session**:

- Event von 18:00–19:30 → Pumpe läuft automatisch von 18:00 bis 19:30
- Der Titel/Summary ist **egal** — nur Start und Ende zählen
- Wartung, Pause, Frostschutz haben Vorrang vor Kalender-Events
- Mit aktiviertem Weather-Guard wird ein Event übersprungen, wenn Regen über der Schwelle vorhergesagt ist

Filter, Stoßchlorung und Pause werden **nicht** kalender-getriggert — dafür gibt es die Buttons der Card oder die Services:

```yaml
service: pool_controller.start_filter
target:
  entity_id: climate.gartenpool_gartenpool
data:
  duration_minutes: 30
```

## Typische Probleme & Lösungen

- **PV-Karte zeigt "Konfigurationsfehler"** → `apexcharts-card` ist nicht installiert (siehe oben).
- **"Pumpe aus" obwohl Steckdose ein ist** → ältere Versionen haben einen Geist-Wert `pump_switch: switch.whirlpool` aus den Setup-Defaults persistiert. Dieser Fork enthält eine **automatische Migration**, die diesen Geist beim ersten Start entfernt. Nach einem Restart sollte die Anzeige korrekt sein.
- **"Nächster Filter in 14 h" trotz 8-h-Intervall** → kein Bug, sondern Quiet-Hours-Verschiebung. Wenn der berechnete Startpunkt in die Ruhezeit fallen würde, wird auf das Quiet-Ende verschoben. Plus: `filter_credit_minutes` (gesammelte Laufzeit aus PV-/Bade-Sessions) zählt gegen den Pflichtfilter.
- **"Konfigurationsfehler" auf der Karte trotz korrekter Integration** → meistens fehlt eine Frontend-Card-Abhängigkeit. Erste Anlaufstelle: Browser-Konsole (F12) → "Failed to load module" Hinweise.

Mehr unter [docs/troubleshooting.md](docs/troubleshooting.md).

## Hausakku-Vorrang vor PV-Pool-Nutzung (Fork-Feature)

Optionales Gate für PV-Optimierung: PV-getriggerte Pool-Läufe werden zurückgehalten, bis der Hausakku einen konfigurierbaren Ladestand erreicht hat. Damit lädt sich die Haus-Batterie zuerst aus dem PV-Überschuss; erst was darüber hinaus übrig ist, geht in den Pool.

**Aktivieren:** Settings → Devices & Services → Pool Controller → CONFIGURE → PV

Drei neue Felder:

- **Hausakku zuerst laden** (Toggle) — Master-Schalter für die Funktion
- **Akku-SOC-Sensor** (EntitySelector, Device-Class `battery`) — z.B. `sensor.battery_level` bei Sungrow, oder beliebiger anderer SOC-Sensor in %
- **Akku-SOC-Schwelle** (0–100 %) — bis zu welchem Stand der Akku geschützt wird. Default: **80 %**

**Verhalten:**

```
PV-Überschuss > Einschaltschwelle?
  └── nein → Pumpe aus
  └── ja → Akku-Vorrang aktiv?
       └── nein → Pumpe an (alte Logik)
       └── ja → Akku-SOC ≥ Schwelle?
            ├── ja → Pumpe an
            └── nein → blockiert (binary_sensor.<pool>_battery_first_blocking = on)
```

**Hysterese:** sobald das Gate geöffnet hat (SOC ≥ Schwelle), schließt es erst wieder, wenn der SOC unter (Schwelle − 2 %) fällt. Verhindert Pulsieren um die Schwelle.

**Sicher per Default:** wenn der SOC-Sensor `unavailable`/`unknown`/außerhalb 0–100 ist, fällt das Gate transparent zurück auf die alte Logik (fail-open). Pflicht-Filterzyklen sind von dem Gate **nicht** betroffen — die laufen immer durch.

**Diagnose-Sensor:** `binary_sensor.<pool>_battery_first_blocking` zeigt live, ob PV-Überschuss da wäre, das Gate ihn aber gerade blockt — praktisch für die Frage "warum läuft die Pumpe nicht obwohl PV verfügbar ist?".

## Unterschiede zum Upstream-Repo

Dieser Fork enthält folgende Fixes (siehe [PR #1](https://github.com/DJ3vil/pool_controller/pull/1) im Fork):

1. **Initial Config Flow funktioniert wieder** — `step_id="init"` → `step_id="user"`, sonst konnte HA den Eintrag nie anlegen.
2. **Keine Geister-Defaults mehr** — Entity-IDs aus dem Original-Setup des Entwicklers (`switch.whirlpool`, `sensor.esp32_5_cd41d8_whirlpool_*`, `calendar.whirlpool`) werden nicht mehr automatisch in jede Neuinstallation kopiert.
3. **Pump-Switch-Fallback robuster** — wenn `pump_switch` auf eine nicht existierende Entity zeigt, wird zur Laufzeit auf den Hauptschalter zurückgefallen statt "Pumpe aus" zu melden.
4. **Migration für Bestands-Konfigurationen** — `_sanitize_legacy_defaults()` läuft einmalig beim Setup und entfernt veraltete Geister-Werte aus bestehenden Config-Entries.
5. **Hausakku-Vorrang vor PV-Pool-Nutzung** (siehe Sektion oben) — PV-getriggerte Pool-Läufe können optional zurückgehalten werden, bis der Hausakku eine SOC-Schwelle erreicht hat.

## Mitwirken

Issues / PRs gerne. Workflow siehe [CONTRIBUTING.md](CONTRIBUTING.md).
