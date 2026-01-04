# Advanced Pool Controller for Home Assistant

Komplette Anleitung zur Installation, Konfiguration und zum Testen der benutzerdefinierten Integration `pool_controller`.

Kurzüberblick
- Domain: `pool_controller`
- Plattformen: `climate`, `sensor`, `binary_sensor`, `switch`, `button`
- Basis: `DataUpdateCoordinator` zur zentralen Datensammlung
- Unterstützte Sensoren: Wassertemperatur, Außentemperatur, pH, Chlor (Redox), PV-Leistung, Leistungssensoren

Anforderungen
- Home Assistant Core 2026 (API-Kompatibilität getestet)
- Python 3.13

Installation (manuell)
1. Kopiere den Ordner `custom_components/pool_controller` in dein Home Assistant `config/custom_components` Verzeichnis.
2. Stelle sicher, dass die Datei `manifest.json` im `pool_controller`-Ordner bleibt.
3. Starte Home Assistant neu oder lade Integrationen neu (Developer Tools → YAML → Restart Core oder Integration neu laden).

Installation via Entwicklung (Dev Container)
1. Öffne das Repository im Dev-Container / VS Code Remote.
2. Kopiere bei Bedarf den Ordner in die HA-Konfigurationsumgebung oder mounte das Repo als Volume in deiner HA-Dev-Instanz.

Konfiguration (UI - Config Flow)
1. In Home Assistant: Einstellungen → Geräte & Dienste → Integration hinzufügen → Suche nach "pool_controller" (oder manuell über Local Custom Component).
2. Durchlaufe den vierstufigen Wizard: Basis → Heizung → Wasserqualität → Logik.
3. Standardwerte sind in `custom_components/pool_controller/const.py` definiert (z. B. Sensor-Entity-IDs, Default-Volumen).

Wichtige Hinweise zum Options Flow
- In Home Assistant 2026 ist `self.config_entry` in `OptionsFlow` schreibgeschützt. Die Integration verwendet nun korrekt `curr = {**self.config_entry.data, **self.config_entry.options}`.

Funktions-Highlights
- Aufheizzeit-Berechnung: t_min = V * 1.16 * ΔT / P * 60 (Minuten). Fallbacks: fehlende Wassertemp → 20°C, fehlende Leistung → 3000 W.
- Kalender-Integration: `calendar.get_events` wird verwendet, um Bade-Events zu lesen und `next_start_mins` zu berechnen.
- Wasserchemie: pH- und Chlor-Berechnungen (Ausgabe in g bzw. Löffeln).
- Stoßchlorung: Button `Kurz Chloren` setzt einen 5‑Minuten-Timer (`quick_chlorine_until`) der priorisiert die Hauptversorgung einschaltet.
- Pause-Funktion: Button `Pausieren` setzt einen Pause-Timer (`pause_until`). Beide Timer werden persistent in `entry.options` gespeichert.

Übersetzungen
- Übersetzungen liegen in `custom_components/pool_controller/translations/` vor: `de.json`, `en.json`, `fr.json`, `es.json`.
- Entity-Namen und Sensor-State-Labels sind über `translation_key` gemappt, UI zeigt lokalisierten Text basierend auf HA-Locale an.

Testen / Validierung
1. Integration neu laden (oder HA neu starten).
2. Prüfe im UI unter Einstellungen → Geräte & Dienste → `pool_controller` die erzeugten Entities.
3. Simuliere Sensorwerte über Entwicklerwerkzeuge → Zustände (Developer Tools → States): setze z. B. `sensor.esp32_5_cd41d8_whirlpool_temperature` auf `30` und beobachte `sensor.pool_controller_next_start_mins` / `sensor.pool_controller_water_temp`.
4. Drücke im UI den Button `Kurz Chloren` und prüfe, dass `sensor.pool_controller_is_quick_chlor` (oder Status) für 5 Minuten `true` bzw. den entsprechenden State anzeigt.
5. Neustart von HA: die `quick_chlorine_until` und `pause_until` Werte sollten aus `entry.options` wiederhergestellt werden.

Logs & Fehlersuche
- Logs prüfen: Supervisor / core logs oder `home-assistant.log` im Konfigurationsverzeichnis.
- Bei Exceptions: Suche nach Einträgen mit `pool_controller` im Log; Debug-Logging kannst du aktivieren, z. B. in `configuration.yaml`:

```yaml
logger:
	default: info
	logs:
		custom_components.pool_controller: debug
```

Unit-Tests (Empfehlung)
- Es gibt aktuell keine umfassenden Tests im Repo. Vorschlag:
	- Erstelle Tests unter `tests/` und nutze `pytest` + `pytest-homeassistant-custom-component` fixtures.
	- Beispiel-Befehl (in einem passenden HA-dev-Environment):

```bash
python -m pip install -r requirements-dev.txt
pytest tests -q
```

Developer-Hinweise
- Code-Stellen:
	- `coordinator.py`: Zentrale Berechnungen, Timer-Persistenz, `should_main_on`-Logik.
	- `config_flow.py`: ConfigFlow & OptionsFlow.
	- `const.py`: Defaults und Config-Keys.
	- `button.py`, `sensor.py`, `switch.py`, `binary_sensor.py`, `climate.py`: Entity-Implementierung.
- Wenn du Änderungen an Übersetzungen machst: Datei in `translations/` anlegen/aktualisieren und Integration in HA neu laden.

Versionierung / PR
- Wenn du die Änderung für ein Release vorbereitest:
	- Bump `version` in `manifest.json` und aktualisiere `hacs.json` falls genutzt.
	- Ergänze Changelog im `README.md` oder `CHANGELOG.md`.

Support / Kontakt
- Für Fragen zur Implementierung kannst du Issues erstellen oder direkt im Repo Änderungen vorschlagen.

---
Stand: v1.1.2 (Test-Release). Änderungen nach v1.1.1: Robustere Heat-Time-Berechnung, Persistenz für Quick-Chlorine/Pause, Übersetzungen erweitert. Lovelace-View und abgeleitete Sensoren hinzugefügt.

Lovelace UI

Eine empfohlene Lovelace-View (fertige YAML) liegt im Repository unter:

- Datei: [lovelace/pool_controller_lovelace.yaml](lovelace/pool_controller_lovelace.yaml#L1-L200)

Kopiere den Inhalt der Datei in deinen Lovelace Raw-Editor (Dashboard → Drei Punkte → Rohkonfiguration) oder lade die Datei als Ressource in dein Dashboard.
