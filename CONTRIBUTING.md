# Contributing (pool_controller)

Danke fürs Mithelfen!

## Repos & Scope
- Backend-Integration: `pool_controller` (dieses Repo)
- Frontend-Card: `pool_controller_dashboard_frontend` (separates Repo)

Wenn du Änderungen machst, prüfe immer, ob der Cross-Repo Vertrag betroffen ist (siehe [AGENTS.md](AGENTS.md)).

## Wichtige Regeln (projektspezifisch)
- `unique_id`-Suffixe sind Teil des API/UX-Vertrags mit dem Frontend (Auto-Discovery via Entity Registry). Suffixe nicht ohne sehr guten Grund ändern.
- Der Coordinator ist „authoritative“: Schaltlogik/State-Machine gehört in den Coordinator; Entities toggeln keine Hardware „nebenbei“.
- Nach Zustandsänderungen immer `await coordinator.async_request_refresh()` auslösen.
- Übersetzungen: Änderungen an Entities/Strings müssen in allen Sprachen gepflegt werden: `custom_components/pool_controller/translations/{de,en,es,fr}.json`.
- Config-/Options-Flow UX: Jeder Tab/Step braucht eine verständliche Kurzbeschreibung (`description`) und jedes Feld eine Erklärung (`data_description`) – in `strings.json` *und* in allen Sprachen (`de/en/es/fr`).

## Release/Test-Workflow (kein lokales HA erforderlich)
Dieses Projekt wird **über HACS via GitHub Releases** deployt und getestet.

- Version bump: `custom_components/pool_controller/manifest.json` → `version`
- Release: GitHub Release erstellen, **Tag-Name = `vX.Y.Z`** (Datei-Version bleibt `X.Y.Z`)
- Test: in Home Assistant via HACS updaten

Konkrete Schritte: siehe [Release-Checkliste in AGENTS.md](AGENTS.md).

## Lokale Dev-Umgebung (optional, für schnelleres Feedback)
Wenn du schneller `homeassistant.*` Imports/Type-Hints und statische Fehler sehen willst (ohne eine Home-Assistant-Instanz laufen zu lassen), nutze die Dev-Abhängigkeiten.

- Variante B (empfohlen): `pytest-homeassistant-custom-component`
	- Installiert passende Home-Assistant-Pakete/Dependencies für Tests/Analyse.
	- Setup:
		- `python3 -m venv .venv`
		- `source .venv/bin/activate`
		- `pip install -r requirements-dev.txt`

Falls die Installation lokal wegen Python-Version/Native-Deps hakt: nutze den vorhandenen Devcontainer in `.devcontainer/` (läuft auf dem `homeassistant/home-assistant:stable` Image und bringt eine kompatible Umgebung mit).

## Was in einen PR gehört
- Klare Beschreibung (Motivation + erwartetes Verhalten)
- Falls neue/umbenannte Entities/Keys: Hinweis, ob Frontend-Mapping/Auto-Discovery betroffen ist
- Übersetzungen in `de/en/es/fr` vollständig

## Akzeptanzkriterien (kurz)
- Breaking Changes nur in Major-Releases (und nur mit Migrationshinweisen/Kommunikation).
- Keine Breaking Changes an `unique_id`-Suffixen ohne sehr guten Grund + Migration/Kommunikation.
- Änderungen an Timern/Services müssen Multi-Instanz-Routing über `climate_entity`/`config_entry_id` berücksichtigen.
- Neue Entities/Keys: `coordinator.data` + Entity-Setup + Übersetzungen (de/en/es/fr) vollständig.
- Config-/Options-Flow Änderungen: Step-`description` und Feld-`data_description` vollständig (inkl. Options-Flow), in `strings.json` sowie `de/en/es/fr`.
- Release-Fähigkeit: `manifest.json` Version-Bump ist Teil der Änderung, wenn HACS-Deploy geplant ist.

## Dateien, die du dir zuerst ansehen solltest
- `custom_components/pool_controller/coordinator.py`
- `custom_components/pool_controller/__init__.py` (Services)
- `custom_components/pool_controller/const.py` (Keys/Defaults)
- `custom_components/pool_controller/translations/`
