# Workspace Agent Instructions (pool_controller + pool_controller_dashboard_frontend)

## Repos im Workspace
- Backend Integration: [custom_components/pool_controller/](custom_components/pool_controller/) (Domain `pool_controller`)
- Frontend Card: getrenntes Repo `pool_controller_dashboard_frontend` (Single-File HACS Plugin: `main.js`)

## Cross-Repo Vertrag (wichtig)
- Frontend auto-discovered Entities über `config/entity_registry/list` und `unique_id`-Suffixe.
- Backend darf `unique_id`-Suffixe nicht „mal eben“ ändern: `${entry_id}_${suffix}` ist Teil des API/UX-Vertrags.
- Timer-Modelle: Frontend bevorzugt neue Minuten-Sensoren (`*_timer_mins` + Attrs `active`, `duration_minutes`, `type`), hat aber Legacy-Fallback.

## Deployment / Test-Workflow (Release-basiert via HACS)
- Ich deploye und teste **ausschließlich via HACS nach neuem GitHub Release** (kein lokales HA nötig).
- Konsequenz für Changes:
  - Backend: Versionsbump in [custom_components/pool_controller/manifest.json](custom_components/pool_controller/manifest.json) (`version`).
  - Frontend: Versionsbump in `main.js` (`const VERSION = "…";`).
  - Danach GitHub Release erstellen (Tag = `vX.Y.Z`, Version in Dateien = `X.Y.Z`) und in HA via HACS aktualisieren.
- Debug bei Frontend-Änderungen: HA Frontend Hard-Reload / Cache leeren; Version-Log in der Console bestätigt geladenes Bundle.

## Release-Checkliste (konkret)
1. Backend ändern (Repo `pool_controller`)
  - Code/Translations anpassen.
  - Version bump: [custom_components/pool_controller/manifest.json](custom_components/pool_controller/manifest.json) → `version` hochsetzen.
  - JSON-Check: Übersetzungen vor Release validieren (z.B. `python -m json.tool`).
  - Übersetzungen via Tools konsolidieren (z.B. `tools/sync_translations.py`).
2. Frontend ändern (Repo `pool_controller_dashboard_frontend`)
  - `main.js` anpassen.
  - Version bump: `main.js` → `const VERSION = "x.y.z";` (muss zum Release-Tag passen).
3. GitHub Releases erstellen
  - Für jedes Repo ein Release/Tag erstellen.
  - Regel: **Tag-Name = `vX.Y.Z`** (Backend-Version in `manifest.json` = `X.Y.Z`, Frontend `VERSION` = `X.Y.Z`).
4. In Home Assistant testen (nur via HACS)
  - HACS Update für Integration + Frontend ausführen.
  - Frontend-Verifikation: Browser Console zeigt `[pool_controller_dashboard_frontend] loaded vX.Y.Z`.
  - Optional: HA Frontend Hard-Reload / Cache leeren, falls altes Bundle gecached ist.

## Änderungsregeln
- Backend: Coordinator ist „authoritative“ (Switch-Calls/State-Machine). Entities sollten keine Hardware direkt schalten.
- Backend: nach Zustandsänderungen immer `await coordinator.async_request_refresh()`.
- Frontend: keine externen Dependencies/Build; alles in `main.js`; Strings über `I18N`/`_t()` (de/en/es/fr).

## Live-Diagnose via Home Assistant API
- Für pool_controller-Livewerte zuerst `python3 tools/ha_api_read.py pool --entity-id climate.whirlpool --compact` nutzen; bei bekannter HA-`device_id` alternativ `--device-id <id>`.
- Im eigenen Netz bevorzugt den direkten HA-Endpunkt verwenden: `python3 tools/ha_api_read.py --local pool --entity-id climate.whirlpool --compact` mit `ha_local_url`/`HA_LOCAL_URL` (aktuell `http://192.168.1.196:8123`) oder `--url http://192.168.1.196:8123`.
- Das Tool akzeptiert globale Optionen vor oder nach dem Subcommand (`states --compact ...` ist gültig) und fällt bei TLS-Zertifikatsfehlern automatisch auf unsichere lokale Verbindung zurück.
- Config-/Options-Werte remote über `python3 tools/ha_api_read.py pool-config --entity-id climate.whirlpool` lesen. Nicht lokale `config/.storage` nutzen; sie hat für Produktion keine Bedeutung. Das Tool nutzt HA WebSocket und nach Release den read-only Service `pool_controller.get_options`.
- Für Dynamic-Target-Debugging liefert `pool` direkt Basis-/Effektivziel, Gesamt-/Saison-/Wetter-Offset, Profil und Wetter-States.

## Übersetzungen / JSON-Qualität
- Vor jedem Release JSON-Lint/Check für die Übersetzungsdateien ausführen.
- Übersetzungen ausschließlich über die Tools im `tools/`-Verzeichnis konsolidieren (z.B. `sync_translations.py` oder `translations_rebuild.py`).

## Wenn du (AI) etwas änderst
- Prüfe, ob Frontend-Autodiscovery oder Service-Calls betroffen sind.
- Bei neuen Entities/Keys: Backend `coordinator.data` + Entity-Klassen + Übersetzungen (de/en/es/fr) + Frontend Mapping (falls nötig).
