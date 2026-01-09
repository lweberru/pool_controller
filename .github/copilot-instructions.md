# pool_controller (Home Assistant Custom Integration)

## Überblick
- Domain: `pool_controller` (HACS Integration). Kern ist ein `DataUpdateCoordinator`-State-Machine-Ansatz.
- Frontend-Karte liegt separat: `pool_controller_dashboard_frontend` (Card: `custom:pc-pool-controller`).

## Workspace / Releases
- Workspace-weite Hinweise: [AGENTS.md](../AGENTS.md) (Cross-Repo Vertrag + Release-basierter HACS Deploy/Test; keine lokale HA-Umgebung erforderlich).

## Architektur / Datenfluss
- `ConfigEntry` → Coordinator in [custom_components/pool_controller/coordinator.py](../custom_components/pool_controller/coordinator.py) (Polling) → `coordinator.data` Dict → Entities in `sensor.py`/`binary_sensor.py`/`switch.py`/`button.py`/`climate.py`.
- Wichtig: Der Coordinator ist „authoritative“ und führt reale Schaltvorgänge aus (Pumpen-/Switch-Calls). Entities sollten nicht eigenständig Hardware toggeln.

## Timer & Persistenz
- Timer werden über `entry.options` als ISO-Datetime gespeichert und beim Start restored (für Neustart-resistente Sessions).
- Nach jeder Zustandsänderung: `await coordinator.async_request_refresh()` (sonst UI/Entities stale).

## Entities / IDs / Übersetzungen
- `unique_id`-Konvention: `${entry_id}_${suffix}` (Suffixe sind Teil des Vertrags mit dem Frontend-Auto-Discovery via Entity Registry).
- Neue Entities/Keys: (1) in Coordinator-Return-Dict hinzufügen, (2) Entity-Klasse registrieren, (3) alle Übersetzungen in [custom_components/pool_controller/translations/](../custom_components/pool_controller/translations/) (de/en/es/fr) nachziehen.

## Services & UX-Vertrag
- Services werden in [custom_components/pool_controller/__init__.py](../custom_components/pool_controller/__init__.py) registriert (Start/Stop für `bathing`, `filter`, `chlorine`, `pause`).
- Climate-Entity in [custom_components/pool_controller/climate.py](../custom_components/pool_controller/climate.py):
  - `hvac_mode` dient als grober Enable/Disable (OFF ↔ Wartung/Lockout).
  - `preset_mode` spiegelt manuelle Timer-Typen (Auto/Baden/Chloren/Filtern/Wartung).

## Config Flow
- Multi-Step Wizard in [custom_components/pool_controller/config_flow.py](../custom_components/pool_controller/config_flow.py) (EntitySelector; „back“-Navigation). Defaults/Keys zentral in [custom_components/pool_controller/const.py](../custom_components/pool_controller/const.py).

## Dev-Workflow (lokal)
- Für schnelle Iteration: Integration in HA `custom_components/` einhängen (Symlink/Copy), Logging für `custom_components.pool_controller` auf `debug`, HA neu starten.
- Demo-Mode beachten: Switch-Calls dürfen im Demo-Mode nicht echte Hardware schalten.
