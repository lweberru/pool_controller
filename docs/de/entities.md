# Sensoren, Entitäten & Steuerung

[English](../entities.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

Die konkreten Entity-IDs hängen vom Namen deiner Instanz ab. Die Integration verwendet aber stabile Suffixe, also translation_key beziehungsweise unique_id-Suffixe, wie unten dargestellt.

## Binary Sensors

| Entität | Beschreibung |
|--------|-------------|
| `binary_sensor.<pool>_is_we_holiday` | Wahr, wenn heute Wochenende oder Feiertag ist |
| `binary_sensor.<pool>_frost_danger` | Wahr, wenn die Außentemperatur unter der konfigurierten Frost-Starttemperatur liegt |
| `binary_sensor.<pool>_frost_active` | Wahr, wenn der Frost-Duty-Cycle aktuell verlangt, dass die Pumpe läuft |
| `binary_sensor.<pool>_in_quiet` | Ruhezeit aktiv |
| `binary_sensor.<pool>_pv_allows` | PV-Überschuss erlaubt Betrieb |
| `binary_sensor.<pool>_away_active` | Away-Modus aktiv |
| `binary_sensor.<pool>_power_saving_active` | Stromsparmodus aktiv |
| `binary_sensor.<pool>_power_saving_available` | Stromsparmodus verfügbar, also alle nötigen Sensoren und Signale vorhanden |
| `binary_sensor.<pool>_sensor_health_problem` | Überwachung der Sensor-Erreichbarkeit meldet eine Störung |
| `binary_sensor.<pool>_sensor_health_esp32_reachable` | Konfiguriertes ESP32-Gerät ist erreichbar |
| `binary_sensor.<pool>_sensor_health_water_sensor_reachable` | Konfigurierter Erreichbarkeitssensor des Wassersensors ist an |
| `binary_sensor.<pool>_should_main_on` | Stromversorgung sollte eingeschaltet sein |
| `binary_sensor.<pool>_should_pump_on` | Umwälzpumpe sollte eingeschaltet sein |
| `binary_sensor.<pool>_main_switch_on` | Physischer Hauptschalter ist aktuell EIN |
| `binary_sensor.<pool>_pump_switch_on` | Physischer Pumpenschalter ist aktuell EIN |
| `binary_sensor.<pool>_aux_heating_switch_on` | Physischer Schalter der Zusatzheizung ist aktuell EIN |
| `binary_sensor.<pool>_aux_present` | Zusatzheizung konfiguriert |
| `binary_sensor.<pool>_low_chlor` | Chlorniveau unter dem empfohlenen Bereich |
| `binary_sensor.<pool>_ph_alert` | pH außerhalb des akzeptablen Bereichs |
| `binary_sensor.<pool>_tds_high` | TDS zu hoch, Wasserwechsel empfohlen |
| `binary_sensor.<pool>_event_rain_blocked` | Nächstes oder laufendes Kalenderevent wird wegen Regenwahrscheinlichkeit blockiert |

## Sensoren numerisch und Status

| Entität | Typ | Beschreibung |
|--------|------|-------------|
| `sensor.<pool>_status` | Enum | Aktueller Zustand: `normal`, `paused`, `frost_protection`, `maintenance`, `away`, `power_saving` |
| `sensor.<pool>_run_reason` | Enum | Warum der Pool gerade läuft: `idle`, `bathing`, `chlorine`, `filter`, `preheat`, `pv`, `frost`, `pause`, `maintenance`, `power_saving` |
| `sensor.<pool>_heat_reason` | Enum | Warum Heizen erlaubt oder aktiv ist: `off`, `disabled`, `bathing`, `preheat`, `pv`, `power_saving` |
| `sensor.<pool>_sensor_health_status` | Enum | Optionaler Status der Sensor-Erreichbarkeit: `disabled`, `unknown`, `ok`, `problem` |
| `sensor.<pool>_sensor_health_message` | Enum | Detail zur Sensor-Erreichbarkeit, z. B. `water_sensor_unreachable` |
| `sensor.<pool>_run_credit_source` | Enum | Aktuelle Credit-Quelle, falls gerade eine Serie läuft |
| `sensor.<pool>_run_credit_minutes` | Integer | Anrechenbare Minuten aus der aktuellen Serie |
| `sensor.<pool>_filter_credit_minutes` | Integer | Effektive Filter-Credit-Minuten |
| `sensor.<pool>_filter_missing_minutes` | Integer | Noch benötigte Filterminuten für den nächsten Zyklus |
| `sensor.<pool>_frost_credit_minutes` | Integer | Effektive Frost-Credit-Minuten |
| `sensor.<pool>_frost_credit_shift_minutes` | Integer | Um wie viele Minuten der Frostzyklus durch Credit verschoben wird |
| `sensor.<pool>_electricity_price` | Float | Strompreis in Währung pro kWh |
| `sensor.<pool>_feed_in_tariff` | Float | Einspeisevergütung in Währung pro kWh |
| `sensor.<pool>_power_cost_per_hour` | Float | Momentane Stromkosten pro Stunde |
| `sensor.<pool>_power_cost_per_hour_net` | Float | Momentane Nettokosten pro Stunde nach PV-Abzug |
| `sensor.<pool>_power_cost_feed_in_loss_per_hour` | Float | Momentaner entgangener Einspeiseertrag pro Stunde |
| `sensor.<pool>_energy_cost_daily` | Float | Brutto-Energiekosten des Tages |
| `sensor.<pool>_energy_cost_monthly` | Float | Brutto-Energiekosten des Monats |
| `sensor.<pool>_energy_cost_yearly` | Float | Brutto-Energiekosten des Jahres |
| `sensor.<pool>_energy_feed_in_loss_daily` | Float | PV-Opportunitätskosten des Tages |
| `sensor.<pool>_energy_feed_in_loss_monthly` | Float | PV-Opportunitätskosten des Monats |
| `sensor.<pool>_energy_feed_in_loss_yearly` | Float | PV-Opportunitätskosten des Jahres |
| `sensor.<pool>_energy_cost_net_daily` | Float | Netto-Energiekosten des Tages |
| `sensor.<pool>_energy_cost_net_monthly` | Float | Netto-Energiekosten des Monats |
| `sensor.<pool>_energy_cost_net_yearly` | Float | Netto-Energiekosten des Jahres |
| `sensor.<pool>_heat_loss_w_per_c` | Float | Gelernter Wärmeverlustkoeffizient in W/°C |
| `sensor.<pool>_heat_startup_offset_minutes` | Float | Gelernte Anlaufverzögerung der Heizung in Minuten |
| `sensor.<pool>_sanitizer_mode` | Enum | Desinfektionsart: `chlorine`, `saltwater`, `mixed` |
| `sensor.<pool>_tds_status` | Enum | Backend-abgeleitete Wasserqualitätsbewertung |
| `sensor.<pool>_ph_val` | Float | Wasser-pH im Bereich 0 bis 14 |
| `sensor.<pool>_chlor_val` | Float | Chlor beziehungsweise ORP in mV |
| `sensor.<pool>_salt_val` | Float | Salzkonzentration in g/L, optional |
| `sensor.<pool>_salt_add_g` | Integer | Empfohlene Salzmenge in Gramm für saltwater oder mixed |
| `sensor.<pool>_tds_val` | Integer | Total Dissolved Solids in ppm |
| `sensor.<pool>_tds_effective` | Integer | Effektives TDS in ppm, bei saltwater oder mixed mit abgezogenem Salz-Baseline |
| `sensor.<pool>_tds_water_change_liters` | Integer | Empfohlenes Wasserwechselvolumen in Litern |
| `sensor.<pool>_tds_water_change_percent` | Integer | Empfohlener Wasserwechsel in Prozent |
| `sensor.<pool>_ph_minus_g` | Float | Empfohlene Menge pH-Minus in Gramm |
| `sensor.<pool>_ph_plus_g` | Float | Empfohlene Menge pH-Plus in Gramm |
| `sensor.<pool>_chlor_spoons` | Float | Empfohlene Chlormenge in Löffeln |
| `sensor.<pool>_next_start_mins` | Integer | Minuten bis zum nächsten Betrieb |
| `sensor.<pool>_next_frost_mins` | Integer | Minuten bis zum nächsten Frostschutzlauf |
| `sensor.<pool>_outdoor_temp` | Float | Außentemperatur in °C |
| `sensor.<pool>_next_event` | Timestamp | Start des nächsten Kalenderevents |
| `sensor.<pool>_next_event_end` | Timestamp | Ende des nächsten Kalenderevents |
| `sensor.<pool>_next_event_summary` | String | Name des nächsten Kalenderevents |
| `sensor.<pool>_event_rain_probability` | Float | Maximale Regenwahrscheinlichkeit des nächsten oder laufenden Events |
| `sensor.<pool>_next_filter_mins` | Integer | Minuten bis zum nächsten Filterzyklus |
| `sensor.<pool>_manual_timer_mins` | Integer | Restminuten des aktiven manuellen Timers mit Attributen `active`, `duration_minutes`, `type` |
| `sensor.<pool>_auto_filter_timer_mins` | Integer | Restminuten des automatischen Filtertimers mit Attributen `active`, `duration_minutes` |
| `sensor.<pool>_pause_timer_mins` | Integer | Restminuten des Pause-Timers mit Attributen `active`, `duration_minutes` |
| `sensor.<pool>_frost_timer_mins` | Integer | Restminuten des aktiven Frostzyklus mit Attributen `active`, `duration_minutes` |
| `sensor.<pool>_pv_power` | Float | PV-Leistung in Watt aus dem konfigurierten Sensor |
| `sensor.<pool>_pv_smoothed` | Float | Geglättete PV-Leistung in Watt für die PV-Hysterese |
| `sensor.<pool>_pv_on_threshold` | Integer | Konfigurierte PV-ON-Schwelle in Watt |
| `sensor.<pool>_pv_off_threshold` | Integer | Konfigurierte PV-OFF-Schwelle in Watt |
| `sensor.<pool>_main_power` | Float | Leistungsaufnahme der Hauptpumpe in Watt |
| `sensor.<pool>_aux_power` | Float | Leistungsaufnahme der Zusatzheizung in Watt |

### Attribute der Minutentimer

Alle vier Timer-Sensoren verwenden **verbleibende Minuten** als Zustand mit der Einheit `min`.

- **Zustand `sensor.*_timer_mins`**: Ganze Minuten Restlaufzeit. Bei Inaktivität ist der Zustand `0`.
- **Aktualisierung**: basiert auf persistierten `*_until`-Zeitstempeln und wird durch den Coordinator regelmäßig aktualisiert, standardmäßig alle 30 Sekunden. Der Wert fällt dadurch schrittweise.

**Gemeinsames Attribut:**
- `active` als bool ist `true`, solange der Timer aktiv ist, sonst `false`.

**Manueller Timer `sensor.<pool>_manual_timer_mins`:**
- `type`: `bathing`, `filter` oder `chlorine`, bei Inaktivität auch `null`
- `duration_minutes`: ursprünglich angeforderte Dauer in Minuten

**Auto-Filter-Timer `sensor.<pool>_auto_filter_timer_mins`:**
- `duration_minutes`: konfigurierte oder gestartete Laufzeit des Auto-Filters

**Pause-Timer `sensor.<pool>_pause_timer_mins`:**
- `duration_minutes`: angeforderte Pausendauer

**Frost-Timer `sensor.<pool>_frost_timer_mins`:**
- `duration_minutes`: konfigurierte Laufzeit des aktuellen Frostzyklus

## Switches

| Entität | Beschreibung |
|--------|-------------|
| `switch.<pool>_main` | Stromversorgung oder Hauptrelais ein/aus |
| `switch.<pool>_pump` | Umwälzpumpe ein/aus |
| `switch.<pool>_aux_allowed` | Zusatzheizung grundsätzlich freigeben |
| `switch.<pool>_aux` | Physischer Netzschalter der Zusatzheizung |

## Climate

| Entität | Beschreibung |
|--------|-------------|
| `climate.<pool>_*` | Thermostat-Entität des Pools; diese Entität sollte in Automationen und in der Dashboard-Karte als Controller gewählt werden. Presets: Auto, Baden, Chloren, Filtern, Abwesend, Wartung, Stromsparen, Boost, Manuell |

`Boost` ist für schnelles Wiederaufheizen gedacht, zum Beispiel nach einem Wasserwechsel. Die Heizanforderung bleibt aktiv, bis die konfigurierte Zieltemperatur erreicht ist; danach endet Boost automatisch. Ruhezeiten werden weiterhin beachtet.

## Buttons und manuelle Steuerung

Die Integration stellt Schnellaktions-Buttons bereit, jeweils mit der Standarddauer:

- `button.<pool>_bath_60` startet Baden für 60 Minuten
- `button.<pool>_filter_30` startet Filterung für 30 Minuten
- `button.<pool>_chlorine_5` startet Schnellchlorung für 5 Minuten
- `button.<pool>_pause_60` startet Pause für 60 Minuten
- `button.<pool>_away_start` aktiviert Away
- `button.<pool>_away_stop` beendet Away

## Statussensoren und Debugging

### Nützliche Diagnose-Sensoren
- `sensor.pool_next_start_mins` für den nächsten geplanten Start
- `sensor.pool_next_frost_mins` für den nächsten Frostschutz-Duty-Cycle in Minuten
- `sensor.pool_next_event` für das nächste Kalenderereignis
- `sensor.pool_run_reason` für den aktuellen Laufgrund
- `sensor.pool_heat_reason` für die Freigabe des Heizens
- `sensor.pool_sensor_health_status` für den optionalen Erreichbarkeitsstatus von ESP32 und Wassersensor
- `binary_sensor.pool_sensor_health_problem` als Störungssignal der Mess-Infrastruktur
- `sensor.pool_run_credit_source` für die aktuelle Credit-Quelle
- `sensor.pool_run_credit_minutes` für die aktuellen Credit-Minuten
- `sensor.pool_filter_credit_minutes` für den effektiven Filter-Credit
- `sensor.pool_filter_missing_minutes` für noch fehlende Filterminuten
- `sensor.pool_frost_credit_minutes` für Frost-Credit
- `sensor.pool_frost_credit_shift_minutes` für die Verschiebung von Frostläufen
- `sensor.pool_heat_loss_w_per_c` für den gelernten Wärmeverlustkoeffizienten
- `sensor.pool_heat_startup_offset_minutes` für die gelernte Startverzögerung
- `sensor.pool_outdoor_temp` als Außentemperatur-Eingang
- `binary_sensor.pool_should_main_on` als Soll-Signal Hauptversorgung
- `binary_sensor.pool_should_pump_on` als Soll-Signal Pumpe
- `binary_sensor.pool_main_switch_on` als Ist-Zustand Hauptschalter
- `binary_sensor.pool_pump_switch_on` als Ist-Zustand Pumpenschalter
- `binary_sensor.pool_aux_heating_switch_on` als Ist-Zustand Zusatzheizung

Debug-Logging in Home Assistant aktivieren:

```yaml
logger:
  logs:
    custom_components.pool_controller: debug
```