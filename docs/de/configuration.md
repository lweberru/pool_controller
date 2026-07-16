# Konfiguration

[English](../configuration.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

## Konfigurationsassistent

Die Integration nutzt einen geführten Assistenten mit 10 bis 11 Schritten, abhängig vom gewählten Desinfektionsmodus.

### Schritt 1: Grundinformationen
- **Name**: Anzeigename für deinen Pool, z. B. Whirlpool Demo
- **Wasservolumen**: Literzahl des Wassers, wichtig für pH- und Chlorberechnungen
- **Demo-Modus**: Aktivieren, um ohne echte Geräte zu testen

### Schritt 2: Schalter und Leistungssensoren
- **Hauptschalter**: Stromversorgung oder Hauptrelais, erforderlich
- **Pumpenschalter**: Umwälzpumpe, optional; wenn leer, nutzt die Integration den Hauptschalter
- **Schalter für Zusatzheizung**: Optionaler zweiter Heizschalter
- **Leistungssensoren**:
  - Hauptleistungssensor in Watt für Laufzeitdiagnosen, Stromsparlogik und Kosten
  - Zusätzlicher Leistungssensor optional

### Schritt 3: Wasserqualitätssensoren (optional)
Nur konfigurieren, wenn du ESP32 plus Blueriiot verwendest:
- **Wassertemperatursensor**: Aktuelle Pooltemperatur
- **pH-Sensor**: pH-Wert des Wassers von 0 bis 14
- **Chlorsensor**: Redox- beziehungsweise ORP-Wert in mV
- **Salzsensor**: Salzkonzentration in g/L, optional
- **Leitfähigkeitssensor**: µS/cm, optional

### Schritt 3b: Überwachung der Sensor-Erreichbarkeit (optional)
- **Sensor-Erreichbarkeit überwachen**: zeigt eine Diagnose-Störung, wenn die konfigurierte Mess-Infrastruktur nicht verfügbar ist
- **ESP32-Gerät**: optionales Gerät, das die Pool-Messwerte bereitstellt; erreichbar, wenn mindestens eine seiner Entities verfügbar ist
- **Erreichbarkeit des Wassersensors**: optionaler Binary-Sensor, der `on` ist, wenn der Wassersensor, z. B. BlueRiiot, erreichbar ist

### Schritt 4: Desinfektion
Pool Controller unterstützt mehrere Desinfektionsarten und passt Teile der Wasserqualitätsbewertung entsprechend an.

- **Desinfektionsmodus**: `chlorine`, `saltwater` oder `mixed` für Salz plus Chlor
- **Schritt 4b nur für Saltwater oder Mixed**: **Ziel-Salzgehalt in g/L** als Basis für die effektive TDS-Bewertung

### Schritt 4c: Chemie-Schätzung (einfaches Tuning)

Dieser Schritt hält Chemie-Empfehlungen praxistauglich, ohne zu viele Expertenparameter offenzulegen.

- **Ziel-TDS in ppm**: Zielwert für Empfehlungen zum Wasserwechsel bei hohem TDS
- **Ziel-Alkalinität in ppm**: Referenzziel für Alkalinitätsmaßnahmen
- **Cooldown nach Aktivität oder Chemiezugabe in Minuten**: blockiert direkte Empfehlungen, solange sich das Wasser noch mischt oder reagiert
- **Fenster für stabile Historie in Minuten**: legt fest, wie weit stabile Samples zurück betrachtet werden
- **Minimale Anzahl stabiler Samples**: erst dann werden belastbare Alkalinitäts-Empfehlungen angezeigt

Für die meisten Installationen reichen die Standardwerte aus.

### Schritt 5: Temperaturregelung (Thermostat)
- **Zieltemperatur**: Gewünschte Wassertemperatur, wird gespeichert
- **Abwesenheitstemperatur**: Zieltemperatur bei aktivem Away-Modus
- **Min/Max/Schrittweite**: Grenzen für die Thermostat-Oberfläche
- **Toleranzen**: Einfache Hysterese für Ein- und Ausschalten

**Verhalten im Away-Modus:**
- setzt die Zieltemperatur auf die Abwesenheitstemperatur
- beendet manuelle Timer und Pause
- lässt automatische Filterung und Frostschutz aktiv

### Schritt 6: Frostschutz
- **Außentemperatursensor**: Grundlage für die Frostschutzlogik
- **Frostschutz-Tuning** optional: Duty-Cycle-Einstellungen und eine Notfallgrenze für Ruhezeiten

### Schritt 7: Kalender und Ruhezeiten
- **Pool-Kalender**: Kalender-Entität für den Betriebsplan
- **Feiertagskalender**: lokale Feiertage werden wie Wochenenden behandelt
- **Weather Guard optional**:
  - **Weather Guard aktivieren**: verhindert Vorheizen und Eventstart bei hoher Regenwahrscheinlichkeit
  - **Weather-Entity**: `weather.*`-Entität mit Unterstützung für `weather.get_forecasts` auf Stundenbasis
  - **Grenzwert Regenwahrscheinlichkeit**: wenn die Vorhersage während des Events mindestens diesen Wert erreicht, wird das Event blockiert
- **Ruhezeiten werktags**: Start- und Endzeit, z. B. 22:00 bis 07:00
- **Ruhezeiten Wochenende**: eigene Start- und Endzeit

**Beispiel für Weather Guard:**

```yaml
# Beispiel: blockiere Pool-Events bei Regenwahrscheinlichkeit ab 60 Prozent
pool_controller:
  enable_event_weather_guard: true
  event_weather_entity: weather.home
  event_rain_probability: 60
```

### Schritt 8: Filtereinstellungen
- **Automatische Filterung**: automatische Filterzyklen ein- oder ausschalten
- **Filterintervall**: Minuten zwischen automatischen Filterzyklen, Standard 720 gleich 12 Stunden
- **Filterdauer**: Standardlaufzeit eines Zyklus in Minuten
- **Merge Window**: Wenn ein Frostlauf nahe liegt, können Filter und Frost zusammengelegt werden
- **Minimum Gap**: Erzwingt eine Pause zwischen Läufen außer bei starkem Frost
- **Max Merged Run**: Obergrenze für zusammengelegte Läufe
- **Minimum Credit**: Sehr kurze Läufe zählen nicht als Gutschrift
- **Credit Sources**: Welche Laufgründe als Gutschrift zählen dürfen, z. B. Filter, Baden, Chlor, Vorheizen, PV, Frost oder Thermostat
- **Deadline-Stunde im Stromsparmodus**: Uhrzeit von 0 bis 23, ab der verschobene Filterläufe spätestens gestartet werden, Standard 16

### Schritt 9: PV-Solarintegration
- **PV-Überschusssensor**: Entität für überschüssige Solarleistung in Watt
- **Faktor für Stromspar-Schwellenwerte in Prozent**: Multiplikator für die Einschaltstufen im Stromsparmodus, Standard 105 Prozent
  - `100%`: Start bei geschätztem Poolbedarf
  - `>100%`: konservativer, lässt PV-Reserve für andere Verbraucher
  - `<100%`: startet früher, kann aber kurze Netzbezugsspitzen verursachen
- **Vorheizen mit Zusatzheizer im Stromsparmodus**: Wenn aktiv, nutzt Vorheizen die Zusatzheizung direkt und die Schätzung berücksichtigt deren Leistung; sonst bleibt der Zusatzheizer an PV-Stufen gekoppelt und die Schätzung rechnet konservativer
- **PV-ON-Schwelle**: schaltet Pumpe oder Heizung ein, wenn der PV-Wert darüber liegt, Standard 1000 W
- **PV-OFF-Schwelle**: schaltet wieder aus, wenn der PV-Wert darunter fällt, Standard 500 W
- **PV-Smoothing-Fenster**: exponentielle Glättung in Sekunden
- **PV-Stabilitätsfenster**: wie lange der geglättete Wert stabil bleiben muss, bevor ein Zustandswechsel erlaubt ist
- **PV-Minimum-Run**: Mindestlaufzeit nach einem automatischen PV-Start in Minuten

### Schritt 10: Stromkosten
- **Strompreis**: fester Preis pro kWh
- **Entität für Strompreis**: dynamische Preis-Entität, überschreibt den festen Preis
- **Einspeisevergütung**: fester Vergütungssatz pro kWh
- **Entität für Einspeisevergütung**: dynamische Entität, überschreibt den festen Wert
- **Pool-Energie Basis/Zusatz**: Gesamt-kWh-Zähler, notwendig für die Kostenberechnung
- **Pool-Energie Basis/Zusatz täglich**: optionale Tageszähler
- **Solarenergie täglich**: optionale tägliche PV-kWh, die dem Pool zugeordnet werden

## Konfigurationsoptionen und Standardwerte

| Einstellung | Standard | Bereich | Hinweise |
|---------|---------|-------|-------|
| Wasservolumen | 1000 | 100-10000 L | Grundlage für pH- und Chlordosierung |
| Desinfektionsmodus | chlorine | chlorine / saltwater / mixed | Beeinflusst, wie TDS interpretiert wird |
| Ziel-Salzgehalt in g/L | 4.0 | 0-10 g/L | Nur für saltwater oder mixed; Basis für effektives TDS |
| Chemie Ziel-TDS | 1200 | 500-3500 ppm | Verwendet für Wasserwechsel-Empfehlungen |
| Chemie Ziel-Alkalinität | 110 | 70-160 ppm | Referenzwert für Alkalinitäts-Empfehlungen |
| Chemie Cooldown | 90 | 0-1440 min | Sperrt Alkalinitäts-Aktionen nach Aktivität oder Chemiezugabe |
| Chemie Lookback-Historie | 360 | 120-1440 min | Fenster für den Median stabiler Samples |
| Chemie Min. stabile Samples | 4 | 2-12 | Mindestzahl stabiler Samples vor einer belastbaren Empfehlung |
| Filterintervall | 720 | 60-10080 min | Zeit zwischen automatischen Filterzyklen |
| Filterdauer | 30 | 5-480 min | Laufzeit eines Filterzyklus |
| Merge Window | 90 | 0-720 min | Läufe können mit Frostläufen zusammengelegt werden |
| Minimum Gap | 45 | 0-360 min | Ruhezeit zwischen Läufen außer bei starkem Frost |
| Max Merged Run | 40 | 5-360 min | Obergrenze für einen zusammengelegten Lauf |
| Minimum Credit | 5 | 0-60 min | Kürzere Läufe zählen nicht als Credit |
| Credit Sources | bathing, filter, frost, preheat, pv, thermostat, chlorine | Liste | Welche Laufgründe Credit liefern |
| Deadline-Stunde Stromspar-Filter | 16 | 0-23 | Ab dieser Stunde werden verschobene Filterläufe erzwungen |
| Badedauer | 60 | 5-480 min | Standarddauer einer Badesitzung |
| Pausendauer | 60 | 5-480 min | Standarddauer einer Pause |
| Frost Starttemperatur | 2°C | -20 bis 10°C | Unterhalb dieses Werts kann Frostgefahr aktiv werden |
| Frost Schwer Temperatur | -2°C | -30 bis 5°C | Unterhalb dieses Werts wird der strenge Duty-Cycle genutzt |
| Frost Mild Intervall | 240 | 1-1440 min | Intervall des milden Frost-Duty-Cycles |
| Frost Mild Laufzeit | 5 | 0-120 min | Laufzeit innerhalb des milden Intervalls |
| Frost Schwer Intervall | 120 | 1-1440 min | Intervall des starken Frost-Duty-Cycles |
| Frost Schwer Laufzeit | 10 | 0-240 min | Laufzeit innerhalb des starken Intervalls |
| Quiet Override Below | -8°C | -30 bis 0°C | Unterhalb dieses Werts darf Frostschutz Ruhezeiten übersteuern |
| Heizungs-Zieltemperatur | 38°C | 10-40°C | Gespeicherte Zieltemperatur |
| Away-Temperatur | 25°C | 10-40°C | Zieltemperatur im Away-Modus |
| Min Temp | 10°C | - | Untere Grenze der Climate-Entität |
| Max Temp | 40°C | - | Obere Grenze der Climate-Entität |
| Temperaturschritt | 0.5°C | - | Schrittweite der Zieltemperatur |
| Cold Tolerance | 1.0°C | - | Einschalten unter Ziel minus Cold Tolerance |
| Hot Tolerance | 0.0°C | - | Ausschalten erst über Ziel plus Hot Tolerance |
| Schnellchlorung Dauer | 5 | 1-30 min | Dauer der Chlor-Boost-Phase |
| PV-ON-Schwelle | 1000 | 0-20000 W | Aktiviert PV-Betrieb oberhalb dieses Werts |
| PV-OFF-Schwelle | 500 | 0-20000 W | Deaktiviert PV-Betrieb unterhalb dieses Werts |
| Stromspar-Faktor | 105 | 50-150 % | Multiplikator für Stufenschwellen im Stromsparmodus |
| Stromspar-Vorheizen nutzt Aux | on | on/off | Wenn on, nutzt Vorheizen im Stromsparmodus den Zusatzheizer direkt |
| PV-Smoothing-Fenster | 60 | 0-3600 s | Exponentielle Glättung, 0 deaktiviert sie |
| PV-Stabilitätsfenster | 120 | 0-86400 s | Erforderliche Stabilität vor Zustandswechsel |
| PV-Minimum-Run | 10 | 0-1440 min | Mindestlaufzeit nach PV-Start |
| Strompreis | 0.30 | 0-5 | Fester Preis pro kWh |
| Entität Strompreis | - | sensor/input_number | Dynamischer Preis, überschreibt festen Wert |
| Einspeisevergütung | 0.08 | 0-5 | Feste Vergütung pro kWh |
| Entität Einspeisevergütung | - | sensor/input_number | Dynamischer Wert, überschreibt festen Tarif |
| Pool Energy Base | - | sensor | Gesamt-kWh-Zähler für Grundlast |
| Pool Energy Aux | - | sensor | Gesamt-kWh-Zähler für Zusatzheizer |
| Pool Energy Base Daily | - | sensor | Tages-kWh-Sensor Grundlast |
| Pool Energy Aux Daily | - | sensor | Tages-kWh-Sensor Zusatzheizer |
| Solar Energy Daily | - | sensor | Tägliche Solar-kWh für den Pool |

Alle Dauereinstellungen können pro Aktion über **Actions** überschrieben werden.

## Adaptives Heiz-Lernen

Die Diagnosewerte `heat_loss_w_per_c` und `heat_startup_offset_minutes` werden automatisch vom Coordinator gelernt und sind keine direkt konfigurierbaren Wizard-Felder.

- `heat_loss_w_per_c` wird aus einer robusten Mehrfach-Sample-Anpassung gelernt, nicht aus einer Einzelmessung.
- Lernen passiert nur während echter Abkühlphasen bei ausgeschaltetem Pool mit Plausibilitätsprüfungen.
- So bleibt die Vorheizschätzung auch im Sommer stabil, wenn Außen- und Wassertemperatur nahe beieinander liegen.