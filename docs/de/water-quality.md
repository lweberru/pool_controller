# Wasserqualitätsüberwachung & Desinfektion

[English](../water-quality.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

## Wasserqualitätsüberwachung mit ESP32 und Blueriiot

### ESP32 einrichten

Die Integration funktioniert am besten mit einem dedizierten ESP32, auf dem ESPHome läuft und der den Blueriiot-Sensor an Home Assistant weiterreicht.

**Warum dieser Ansatz sinnvoll ist:**
- Die Funktionen der Blueriiot-App werden durch Home Assistant ersetzt.
- Die Wasserwerte stehen in Echtzeit für Entscheidungen des Pool Controllers zur Verfügung.
- Es wird weder ein Abo noch eine proprietäre App benötigt.

### Erforderlicher Blueriiot-Sensor

[**Blue Connect GO**](https://www.blueriiot.com/eu-en/products/blue-connect-go) als drahtloser BLE-Sensor zur Wasserqualitätsüberwachung

**Misst:**
- Temperatur mit etwa ±0,5°C Genauigkeit
- pH mit etwa 0,1 pH Genauigkeit
- ORP beziehungsweise Redox als Chlor-Hinweis in mV
- Salzkonzentration in g/L
- Wasserleitfähigkeit in µS/cm
- Batteriestand

### Beispielkonfiguration für ESP32

Ein vollständiges Referenzbeispiel liegt im Repository-Stamm als `esphome-blueriiot-example.yaml`.

### Empfohlen: Native Auslesung über ESPHome-Bluetooth-Proxy

Die bevorzugte Variante ist `esphome-blueriiot-proxy-example.yaml`. ESPHome arbeitet darin nur als Bluetooth-Proxy; Pool Controller führt die proprietäre BlueRiiot-GATT-Abfrage selbst über Home Assistant Bluetooth aus.

1. `esphome-blueriiot-proxy-example.yaml` auf den ESP32 flashen und das Gerät in der ESPHome-Integration hinzufügen.
2. Im Einrichtungs- oder Optionsassistenten von Pool Controller **BlueRiiot direkt auslesen** aktivieren und die Bluetooth-Adresse wählen. Nahe Geräte werden automatisch gefunden; eine MAC-Adresse kann weiterhin manuell eingetragen werden.
3. Ausleseintervalle für Tag und Nacht festlegen. Die Dashboard-Karte und der Button **BlueRiiot jetzt auslesen** können eine sofortige Messung anstoßen, ohne die BLE-Verbindungssperre zu umgehen.

Das Proxy-Profil behält Display und Hardware-Button. Die angezeigten Werte liefert Pool Controller über eine ESPHome-API-Action, deshalb müssen bei einer Änderung des Instanznamens keine generierten Home-Assistant-Entity-IDs mehr in der YAML angepasst werden.

Das Proxy-Profil und das alte direkte `ble_client`-Profil dürfen nicht gleichzeitig für denselben BlueRiiot laufen. `esphome-blueriiot-example.yaml` bleibt als direkter ESPHome-Fallback erhalten.

```yaml
substitutions:
  name: esp32-5
  roomname: Garten
  staticip: 192.168.1.205
  blueriiot1_mac: '00:A0:50:C7:46:C9'
  blueriiot1_name_prefix: 'whirlpool'
  blueriiot1_id_prefix: 'p2'

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: esp-idf
    version: recommended
  flash_size: 16MB
  variant: ESP32S3

# ... weiterer Teil für BLE-Scanning, Display, Sensoren usw.
```

### Sensorwerte im Pool Controller

Nach der Konfiguration übernimmt die Integration automatisch:
- Empfehlungen für pH-Korrekturen mit pH-Minus und pH-Plus
- Empfehlungen für Chlordosierung
- TDS-Überwachung und Wasserwechsel-Empfehlungen
- Warnung bei niedrigem Chlor, typischerweise ORP kleiner 400 mV
- Warnung bei pH außerhalb des Zielbereichs
- Anzeige aller Messwerte als Sensoren

Dieses Kapitel dokumentiert außerdem die **Wartungs- und Empfehlungssensoren** der Integration sowie die zugrunde liegenden Heuristiken für pH, Chlor oder ORP, Salz sowie TDS und Wasserwechsel.

## Wartung & Empfehlungen

Die Dashboard-Karte [pool_controller_dashboard_frontend](https://github.com/lweberru/pool_controller_dashboard_frontend) stellt diese Empfehlungen in ihrem Bereich **Wartung** dar.

Hinweis: Alle Empfehlungen sind Heuristiken und hängen von korrekten Eingaben wie Wasservolumen und Sensor-Kalibrierung ab. Verwende zusätzlich immer deinen eigenen Sachverstand sowie die Vorgaben der eingesetzten Chemieprodukte.

Wichtig: Das ist **keine** Laboranalyse. Pool Controller liefert eine robuste, betriebsorientierte Schätzung, die tägliche Entscheidungen unterstützen soll.

### Überblick über Empfehlungssensoren

Typische Empfehlungssensoren, die konkrete Entity-ID hängt vom Instanznamen ab:

- `sensor.<pool>_ph_plus_g` für Gramm pH-Plus
- `sensor.<pool>_ph_minus_g` für Gramm pH-Minus
- `sensor.<pool>_chlor_spoons` für Chlordosierung in Löffeln auf Basis des ORP-Werts
- `sensor.<pool>_salt_add_g` für Salzmenge in Gramm bei saltwater oder mixed
- `sensor.<pool>_tds_water_change_liters` für empfohlenes Wasserwechselvolumen in Litern
- `sensor.<pool>_tds_water_change_percent` für empfohlenen Wasserwechsel in Prozent

Verwandte Kontextsensoren:

- `sensor.<pool>_sanitizer_mode` mit `chlorine`, `saltwater` oder `mixed`
- `sensor.<pool>_tds_val` als rohes berechnetes TDS in ppm
- `sensor.<pool>_tds_effective` als effektives TDS in ppm, bei saltwater oder mixed abzüglich des Salz-Baselines
- `sensor.<pool>_tds_status` mit `optimal`, `good`, `high`, `critical`, `urgent`
- `binary_sensor.<pool>_tds_high` signalisiert, dass ein Wasserwechsel sinnvoll ist

Zusätzliche Chemie-Kontextsensoren:

- `sensor.<pool>_alkalinity_estimated_ppm` als historiengeglättete Alkalinitätsschätzung in ppm
- `sensor.<pool>_alkalinity_action` mit den Empfehlungen `none`, `measure_first`, `raise_bicarbonate`, `lower_ph_minus`, `water_change_then_adjust`
- `sensor.<pool>_alkalinity_step_dose_g` für die empfohlene Dosis pro Schritt in Gramm
- `sensor.<pool>_alkalinity_steps` für die empfohlene Anzahl Schritte
- `sensor.<pool>_alkalinity_wait_minutes` für die Wartezeit bis zum erneuten Messen

Die vollständige Entitätenliste steht unter [Sensoren, Entitäten & Steuerung](entities.md).

### Welche Eingaben in die Berechnung einfließen

- Wasservolumen in Litern aus `water_volume`
- pH über den als `ph_sensor` konfigurierten Sensor
- Chlor oder ORP in mV über den als `chlorine_sensor` konfigurierten Sensor
- Leitfähigkeit in µS/cm über `tds_sensor`
- Salzkonzentration in g/L über `salt_sensor`
- Ziel-Salzgehalt in g/L über `target_salt_g_l` bei saltwater oder mixed
- Chemie-Tuning-Optionen:
  - `chem_target_tds_ppm`
  - `chem_target_alkalinity_ppm`
  - `chem_cooldown_minutes`
  - `chem_history_lookback_minutes`
  - `chem_min_stable_samples`

## Robustheit & Historie: warum Einzelmessungen nicht reichen

Um falsche Empfehlungen nach Baden, Chemiezugabe oder plötzlichen Sensorsprüngen zu vermeiden, arbeitet die Integration mit einem abgesicherten Historienmodell.

- Empfehlungen werden während aktiver Störfenster blockiert, z. B. bei Baden, Chlorung, Boost, Pause oder Wartung.
- Nach relevanten Aktivitäten gilt ein Cooldown-Fenster `chem_cooldown_minutes`.
- Plötzliche Sensor-Sprünge lösen ebenfalls eine temporäre Sperre aus.
- Nur **stabile** Samples werden für belastbare Empfehlungen berücksichtigt.
- Eine Empfehlung gilt erst dann als belastbar, wenn mindestens `chem_min_stable_samples` stabile Werte innerhalb des konfigurierten Zeitfensters `chem_history_lookback_minutes` vorliegen.
- Die eigentliche Schätzung basiert auf dem **Median** der stabilen Historie und ist dadurch robuster gegen Ausreißer.

Diese Historie wird in den Optionen des Config Entry persistiert, damit Home-Assistant-Neustarts die Lern- und Bewertungsqualität nicht zurücksetzen.

## Dosierung zur pH-Korrektur

**Formeln mit Toleranzbereich:**

```text
Ziel-pH: 7.2
OK-Bereich: 7.0 bis 7.4, keine Dosierung nötig

pH-Minus in Gramm = (Aktueller pH - 7.2) × 100 × Volumen in m³  nur wenn pH > 7.4
pH-Plus in Gramm = (7.2 - Aktueller pH) × 100 × Volumen in m³  nur wenn pH < 7.0
```

## Berechnung der Chlordosierung

**Formel** auf Basis eines Referenzvolumens von 1000 Litern:

```text
Ziel: 700 mV als idealer Chlorbereich
Pro 100 mV unter 700 -> +0.25 Löffel für 1000 Liter
Gerundet auf 0.25-Löffel-Schritte

chlorine_spoons = round((700 - chlor_mV) / 100) / 4 × (volume_L / 1000)
```

## Desinfektionsmodus chlorine, saltwater oder mixed

Pool Controller kann mit unterschiedlichen Desinfektionskonzepten arbeiten:

- `chlorine`: klassischer Chlorpool; die Wasserqualitätsbewertung nutzt das rohe, abgeleitete TDS
- `saltwater`: Salzchlorinator-Systeme; Leitfähigkeit und TDS werden stark vom Salz dominiert, deshalb berechnet Pool Controller ein **effektives TDS** als Näherung für nicht-salzige gelöste Stoffe
- `mixed`: Kombination aus Salzsystem und zusätzlicher Chlordosierung; ebenfalls mit **effektivem TDS**

Der gewählte Modus wird bereitgestellt über:
- `sensor.<pool>_sanitizer_mode`

Bei Upgrades von älteren Versionen wird der alte Bool-Wert `enable_saltwater` weiterhin erkannt, die bevorzugte Konfiguration ist aber `sanitizer_mode`.

## Salzempfehlung bei saltwater und mixed

Relevant nur, wenn `sanitizer_mode` **saltwater** oder **mixed** ist.

- Aktuelle Salzkonzentration: `sensor.<pool>_salt_val` in g/L
- Ziel-Salzkonzentration: Option `target_salt_g_l` in g/L

Mit `volume_L` als konfiguriertem Poolvolumen gilt:

```text
missing_g_l = max(0, target_salt_g_l - salt_g_l)
salt_add_g = round(missing_g_l * volume_L)
```

Diese Empfehlung wird ausgegeben als:
- `sensor.<pool>_salt_add_g` in Gramm

Wenn alles im Zielbereich ist oder der Wert nicht anwendbar ist, liefert der Sensor `0`.

## TDS und Empfehlung zum Wasserwechsel

Wenn du einen **Leitfähigkeitssensor** bereitstellst, üblicherweise aus Blueriiot, leitet Pool Controller daraus **TDS in ppm** ab und schätzt, wie viel Wasser ersetzt werden sollte, um wieder in Richtung Zielwert zu kommen.

### 1) Umrechnung Leitfähigkeit nach TDS

Die Integration erwartet Leitfähigkeit in **µS/cm** und wandelt sie mit einem Standardfaktor in TDS um:

```text
tds_ppm = round(conductivity_uS_cm × 0.64)
```

Dieser Wert erscheint als:
- `sensor.<pool>_tds_val` in ppm

### 1b) Effektives TDS bei saltwater und mixed

In `saltwater` und `mixed` spiegelt rohe Leitfähigkeit beziehungsweise TDS vor allem den gewünschten Salzanteil wider. Damit das System nicht permanent "zu hoch" meldet, rechnet Pool Controller:

```text
salt_baseline_ppm = target_salt_g_l × 1000
tds_effective = max(0, tds_val - salt_baseline_ppm)
```

Dieser Wert erscheint als:
- `sensor.<pool>_tds_effective` in ppm

Status, Warnungen und Wasserwechsel-Empfehlungen basieren auf **effektivem TDS**, wenn es verfügbar ist, sonst auf dem rohen `tds_val`.

### 2) TDS-Status und Warnungen

Auf Basis des für die Wartungsbewertung verwendeten ppm-Werts setzt die Integration einen Status und einen binären Alarm:

- `sensor.<pool>_tds_status` mit `optimal`, `good`, `high`, `critical`, `urgent`
- `binary_sensor.<pool>_tds_high` auf `on`, wenn ein Wasserwechsel empfohlen ist

Aktuelle Backend-Schwellenwerte:

- unter `1500 ppm` -> `optimal`
- unter `2000 ppm` -> `good`
- unter `2500 ppm` -> `high`
- unter `3000 ppm` -> `critical`
- ab `3000 ppm` -> `urgent`

Ab `high` wird `tds_high` gesetzt.

### 3) Empfohlener Wasserwechsel in Litern und Prozent

Um zu schätzen, wie viel Wasser ersetzt werden sollte, nutzt die Integration ein einfaches Verdünnungsmodell mit einem Ziel-TDS:

- Ziel-TDS: `chem_target_tds_ppm`, Standard `1200 ppm`

Formel, verwendet den Wartungs-TDS-Wert, also effektiv wenn vorhanden, sonst roh:

```text
water_change_liters = round(volume_L × (tds_maint_ppm - target_ppm) / tds_maint_ppm)   nur wenn tds_maint_ppm > target_ppm
water_change_percent = round((water_change_liters / volume_L) × 100)
```

Diese Empfehlungen werden bereitgestellt als:
- `sensor.<pool>_tds_water_change_liters` in Litern
- `sensor.<pool>_tds_water_change_percent` in Prozent

## Alkalinitätsschätzung und belastbare Handlungsempfehlungen

Pool Controller schätzt die Alkalinität als ppm CaCO3 aus dem verfügbaren Chemiekontext und leitet daraus praktikable Schritte ab.

### 1) Rohschätzung als Heuristik

Die Rohschätzung stützt sich auf:

- effektives TDS beziehungsweise rohes TDS, falls kein effektives TDS verfügbar ist
- pH-Abweichung rund um 7.2
- optional einen kleinen Korrektureinfluss aus dem ORP-Wert

Der Rohwert wird vor der Historienglättung auf einen praxisgerechten Bereich begrenzt.

### 2) Historienglättung und Validitätsprüfung

- Rohwerte werden zusammen mit Stabilitätsinformationen in die Chemie-Historie geschrieben.
- Der Median der stabilen Historie bildet die finale Schätzung.
- Reicht die Qualität der Historie nicht aus, fällt die Aktion auf `measure_first` zurück.

### 3) Mapping auf Aktionen

Unter Verwendung von `chem_target_alkalinity_ppm`, Standard `110 ppm`, klassifiziert der Controller und empfiehlt:

- `raise_bicarbonate`: Alkalinität zu niedrig, Bicarbonat schrittweise zugeben
- `lower_ph_minus`: Alkalinität zu hoch, schrittweise mit pH-Minus senken
- `water_change_then_adjust`: Wenn TDS zu hoch ist, zuerst Wasser wechseln und danach neu bewerten
- `none`: keine Aktion nötig
- `measure_first`: noch nicht genug stabile Evidenz

Zusätzliche Schrittwerte werden über Sensoren wie `total_dose`, `step_dose`, `steps` und `wait_minutes` bereitgestellt und sind für schrittweise Dosierung mit Messpausen ausgelegt.