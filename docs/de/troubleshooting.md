# Fehlersuche

[English](../troubleshooting.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

## Sprachunterstützung

Die Integration bringt vollständige Übersetzungen mit für:
- **Deutsch**
- **English**
- **Español**
- **Français**

Entitätsnamen, Buttons und Konfigurationsbeschriftungen werden automatisch anhand der in Home Assistant gesetzten Sprache angezeigt.

## Fehler "Unknown entity" während der Einrichtung
- Prüfe, ob die Sensor-Entity-IDs in deiner HA-Instanz wirklich existieren.
- Optionale Sensoren können leer bleiben, wenn du sie nicht verwendest.
- Achte auf die exakte Schreibweise der Entity-IDs inklusive Groß- und Kleinschreibung.

## Pool schaltet nicht ein
- Prüfe `binary_sensor.pool_should_main_on` und `binary_sensor.pool_should_pump_on`.
- Für den Vergleich von Soll und Ist:
  - `binary_sensor.pool_should_main_on` gegen `binary_sensor.pool_main_switch_on`
  - `binary_sensor.pool_should_pump_on` gegen `binary_sensor.pool_pump_switch_on`
- Prüfe Ruhezeiten und Kalenderereignisse.
- Stelle sicher, dass Frostschutz nicht aktiv ist.
- Prüfe `sensor.pool_status` für den aktuellen Zustand.

## Heizung arbeitet nicht
- Prüfe, ob ein Leistungssensor konfiguriert ist und Werte liefert.
- Prüfe die Zieltemperatur im Climate-Thermostat, Standard 38°C.
- Stelle sicher, dass ein Kalenderereignis aktiv ist, falls dein Ablauf das voraussetzt.
- Prüfe PV-Schwellenwerte, wenn Heizen von Solarüberschuss abhängt.

## Wasserqualitätssensor aktualisiert nicht
- Prüfe, ob der Blueriiot-Sensor in Reichweite ist und Strom hat.
- Prüfe WLAN-Verbindung und ESPHome-Status des ESP32.
- Prüfe die BLE-Verbindung in den ESP32-Logs.
- Starte bei Bedarf den Button **Start BLE Scan** auf dem ESP32.

## Support

Für Probleme, Fragen oder Feature-Wünsche:
1. Prüfe vorhandene GitHub-Issues.
2. Prüfe die Home-Assistant-Logs unter **Einstellungen → System → Protokolle**.
3. Erstelle ein neues GitHub-Issue mit:
   - Version von Pool Controller
   - Version von Home Assistant
   - Details zu deinem Setup
   - Relevanten Logs oder Fehlermeldungen