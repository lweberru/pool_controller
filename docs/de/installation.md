# Installation & Einrichtung

[English](../installation.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

## Hardware-Anforderungen

### Grundausstattung
1. **Smart Switch** für die Hauptpumpe des Pools oder Whirlpools, also ein Ein/Aus-Relais mit WiFi oder Zigbee und Home-Assistant-Anbindung
2. **Home Assistant** mit Unterstützung für Custom Components
3. **Optional: Temperatursensoren**
   - Wassertemperatur für Heizberechnungen
   - Außentemperatur für den Frostschutz

### Für Wasserqualitätsüberwachung (optional, aber empfohlen)
1. **ESP32-Mikrocontroller** wie z. B. ein ESP32-S3-DevKitC-1
2. **Blueriiot-Sensor** [Blue Connect GO](https://www.blueriiot.com/eu-en/products/blue-connect-go)
   - Misst Temperatur, pH, ORP beziehungsweise Chlor, Salz, Leitfähigkeit und Batteriestatus
3. **ESPHome-Konfiguration** als Referenzvorlage

### Für Zusatzheizung (optional)
- Zweiter Smart Switch zur Steuerung eines zusätzlichen Heizgeräts

## Mein persönliches Setup (Beispiel)

Das ist die Konfiguration, mit der ich Pool Controller selbst nutze, als konkrete Referenz:

- Softub Poseidon X
- Anbindung über Zigbee-Smart-Plug mit ZHA
- Blueriiot Blue Connect Go für die Messwerte
- ESP32 zum Auslesen der Blueriiot-Daten
- 2500-W-Tauchsieder als Zusatzheizung
- Tauchsieder ebenfalls über Zigbee-Smart-Plug geschaltet

## Installation der Custom Component über HACS (empfohlen)

1. Stelle sicher, dass [HACS](https://hacs.xyz/) in deiner Home-Assistant-Instanz installiert ist.
2. Öffne **HACS → Integrationen → ⋮ (Menü) → Benutzerdefinierte Repositories**.
3. Füge dieses benutzerdefinierte Repository hinzu:
   - **Repository**: `https://github.com/lweberru/pool_controller`
   - **Kategorie**: `Integration`
4. Klicke auf **Erstellen**.
5. Öffne **HACS → Integrationen** und suche nach **Pool Controller**.
6. Klicke auf **Installieren**.
7. Starte Home Assistant neu.
8. Öffne **Einstellungen → Geräte & Dienste → Integration hinzufügen → Pool Controller**.

## Dashboard-Karte (separates HACS-Plugin)

Die im README gezeigte Dashboard-Karte ist als separates HACS-Plugin verfügbar:

**Repository**: [lweberru/pool_controller_dashboard_frontend](https://github.com/lweberru/pool_controller_dashboard_frontend)

**Installation:**
1. Öffne **HACS → Frontend → ⋮ (Menü) → Benutzerdefinierte Repositories**.
2. Füge das benutzerdefinierte Repository hinzu:
   - **Repository**: `https://github.com/lweberru/pool_controller_dashboard_frontend`
   - **Kategorie**: `Lovelace`
3. Klicke auf **Hinzufügen**.
4. Suche nach **Pool Controller Dashboard** und installiere das Plugin.
5. HACS registriert die Ressource automatisch unter `/hacsfiles/pool_controller_dashboard_frontend/main.js`.
6. Füge die Karte deinem Dashboard hinzu:
   - **Typ**: `custom:pc-pool-controller`
   - **Konfiguration**: Im Karteneditor am besten **Automatically load from instance** nutzen

**Funktionen:**
- Echtzeit-Anzeige für Wasserqualität wie pH, Chlor, Salz und TDS
- Schnellaktionen für Pause, Baden, Filtern und Schnellchlorung
- Temperaturanzeige und Klimasteuerung
- Timer-Anzeigen für alle aktiven Sitzungen
- Statusanzeigen und Warnhinweise
- Anpassbare Themes und Layouts
- Mehrsprachige Oberfläche in de, en, es und fr

## Alternative: Manuelle Installation

Wenn du ohne HACS installieren möchtest:

1. Kopiere das Verzeichnis `custom_components/pool_controller` in deinen Home-Assistant-Ordner `custom_components/`.
2. Starte Home Assistant neu.
3. Öffne **Einstellungen → Geräte & Dienste → Integration hinzufügen → Pool Controller**.