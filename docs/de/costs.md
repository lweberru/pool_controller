# Kosten & Strompreise

[English](../costs.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

Dieses Kapitel erklärt, wie die Integration Kosten berechnet, welche Sensoren relevant sind und was bei dynamischen Strompreisen wichtig ist.

Ziel dieses Bereichs ist, die teils erheblichen Stromkosten des Pools sichtbar zu machen und den Effekt einer PV-Anlage sowie eines PV-ausgerichteten Poolbetriebs zu quantifizieren. Das Credit-System hilft zusätzlich, Kosten zu reduzieren, indem Läufe zusammengelegt oder verschoben werden, während geplante Badezeiten mit Vorheizen trotzdem pünktlich die gewünschte Zieltemperatur erreichen.

## Kostentipp: Stromsparmodus für die niedrigsten Betriebskosten

Wenn dein Schwerpunkt auf **minimalen Betriebskosten** liegt, ist für den Alltag in der Regel der **Stromsparmodus** (`Stromsparen`) die beste Wahl.

Warum er meist am günstigsten ist:
- Laufzeit wird bevorzugt in Phasen mit verfügbarer PV gelegt.
- Automatische Filterläufe werden verschoben, solange PV nicht ausreicht.
- Verschobene Filterläufe werden erst ab der konfigurierten Deadline-Stunde `power_saving_filter_deadline_hour` erzwungen, wodurch teure Netzlaufzeit in Hochpreisfenstern reduziert wird.

Praktische Empfehlung:
- Nutze **Auto**, wenn Komfort und präzises Timing wichtiger sind.
- Nutze **Stromsparen**, wenn Kostenminimierung und PV-Eigenverbrauch wichtiger sind.

Wichtige Abwägungen im Stromsparmodus:
- Automatische Läufe können gestreckt oder verschoben werden, dadurch kann die Gesamt-Laufzeit steigen.
- In manchen Setups ist pumpenorientiertes Aufheizen weniger effizient als ein früherer oder stärkerer Einsatz der Zusatzheizung.

Empfohlener Quick-Check:
- Miss 3 bis 7 vergleichbare Tage in **Auto** und in **Stromsparen**.
- Notiere pro Modus tägliche Poolenergie in kWh, tägliche Laufzeit in Minuten und den geschätzten PV-Anteil des Poolverbrauchs zwischen 0 und 1.
- Berechne die ungefähren täglichen Nettokosten mit:

```text
cost_net ≈ E × (p_grid - PV_share × (p_grid - p_feed))
```

Dabei gilt:
- `E` = täglicher Poolverbrauch in kWh pro Tag
- `p_grid` = mittlerer Netzstrompreis in €/kWh
- `p_feed` = Einspeisevergütung in €/kWh

Dann vergleiche:

```text
savings_day ≈ cost_net_auto - cost_net_ps
runtime_increase_% ≈ (runtime_ps - runtime_auto) / runtime_auto × 100
```

Faustregel:
- Lass Stromsparen als Standard aktiv, wenn `savings_day` positiv ist und die längere Laufzeit beziehungsweise Geräuschkulisse akzeptabel bleibt.
- Wechsle in Auto, wenn Komfort, Timing oder schnelleres Aufheizen wichtiger sind.

## Grundlagen

Kosten basieren auf **Energie in kWh** multipliziert mit dem **Strompreis in €/kWh**. Der Preis kann **fest** oder **dynamisch** sein.

- **Fester Preis**: Wert aus der Konfiguration
- **Dynamischer Preis**: Entität aus der Konfiguration, z. B. ein stündlich wechselnder Tarif

Die Integration berechnet Kosten **zeitgewichtet pro Tag** und leitet daraus Monats- und Jahreswerte ab. Das ist nötig, damit dynamische Preise korrekt einfließen.

## Welche Energiesensoren verwendet werden

Für die Kostenberechnung bevorzugt die Integration tägliche kWh-Sensoren, wenn sie konfiguriert sind. Wenn keine Tagessensoren vorhanden sind, wird ein **Tagesdelta** aus **Gesamtzählern** abgeleitet.

**Konfiguration im Config Flow:**
- `pool_energy_entity_base` als Gesamt-kWh-Zähler
- `pool_energy_entity_aux` als Gesamt-kWh-Zähler
- `pool_energy_entity_base_daily` optional als Tages-kWh
- `pool_energy_entity_aux_daily` optional als Tages-kWh
- `solar_energy_entity_daily` optional als tägliche Solar-kWh für die Netto-Berechnung
- `pv_surplus_sensor` als PV-Leistung in Watt
- `pv_house_load_sensor` optional als Hauslast in Watt, damit interner PV-Überschuss ohne Templates berechnet werden kann

## Sensoren und ihre Bedeutung

**Täglich, monatlich, jährlich relevant:**
- `sensor.<pool>_energy_cost_daily`
- `sensor.<pool>_energy_cost_monthly`
- `sensor.<pool>_energy_cost_yearly`
- `sensor.<pool>_energy_cost_net_daily`
- `sensor.<pool>_energy_cost_net_monthly`
- `sensor.<pool>_energy_cost_net_yearly`

**Einspeiseverlust als Opportunitätskosten:**
- `sensor.<pool>_energy_feed_in_loss_daily`
- `sensor.<pool>_energy_feed_in_loss_monthly`
- `sensor.<pool>_energy_feed_in_loss_yearly`

**Momentanwerte zur Orientierung:**
- `sensor.<pool>_power_cost_per_hour` für Bruttokosten pro Stunde
- `sensor.<pool>_power_cost_per_hour_net` für Nettokosten pro Stunde mit PV-Abzug

## Netto gegen Brutto

- **Bruttokosten**: Netzenergie mal Preis, ohne PV-Gutschrift
- **Nettokosten**: Bruttokosten minus PV-Anteil, sofern `solar_energy_entity_daily` konfiguriert ist

`pv_surplus_sensor` wird als aktuelle PV-Erzeugungsleistung in Watt interpretiert. Wenn zusätzlich `pv_house_load_sensor` gesetzt ist, berechnet die Integration den verfügbaren PV-Überschuss intern als:

```text
production - (house_load - pool_load)
```

**Fallbacks:**
- Wenn `solar_energy_entity_daily` fehlt, nutzt die Netto-Tageskostenberechnung eine zeitgewichtete PV-Gutschrift aus der momentanen Überlappung von Poollast und PV-Überschuss.
- Wenn nur Gesamtlastsensoren existieren, werden Tageswerte weiterhin über Deltas abgeleitet.

So bleiben `net` und `gross` in typischen PV-Setups auch ohne dedizierten Tages-Pool-Solar-kWh-Sensor sinnvoll getrennt.

## Warum es keine Periodenkosten mehr gibt

Periodensensoren für Kosten seit einem unbekannten Startdatum sind bei **dynamischen Preisen** wenig aussagekräftig, weil sich der Preis über die Zeit ändert. Deshalb wurden diese Sensoren entfernt.

## Tipps für saubere Werte

- Verwende wenn möglich **Utility Meter** oder echte **Tages-kWh-Sensoren**.
- Wenn nur Gesamtzähler vorhanden sind, leitet die Integration Tageskosten per Delta ab.
- Achte darauf, dass alle Energiesensoren **monoton** sind und nicht unerwartet zurückgesetzt werden.

## Weiterführende Links

- Vollständige Entitätenliste: [Sensoren, Entitäten & Steuerung](entities.md)