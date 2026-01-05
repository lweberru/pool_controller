# Copilot / AI Agent Hinweise — pool_controller

Kurz: Konzentriere dich auf Home Assistant Custom Component Patterns in `custom_components/pool_controller`.

1) Big Picture
- Domain: `pool_controller` (siehe `manifest.json`). Integration ist ein Home Assistant custom component mit Config Flow, mehreren Plattformen (sensor, switch, climate, binary_sensor, button).
- Datenfluss: `config_entry` → `PoolControllerDataCoordinator` (DataUpdateCoordinator) → Plattform-Entities (lesen `coordinator.data`).
- Wichtige Persistenz: kurzzeitige Timers werden in `entry.options` persistiert (z. B. `quick_chlorine_until`) via `hass.config_entries.async_update_entry`.

2) Schlüsseldateien (Beispiele)
- `custom_components/pool_controller/manifest.json` — Domain, version, iot_class.
- `__init__.py` — erstellt `PoolControllerDataCoordinator`, speichert `hass.data[DOMAIN][entry.entry_id]`, lädt PLATFORMS.
- `coordinator.py` — zentrale Logik: `_async_update_data` liefert ein Dict mit Schlüsseln wie `should_main_on`, `is_paused`, `next_start_mins`.
- `sensor.py` / `switch.py` — konsumieren `coordinator.data`; `unique_id`-Pattern: `f"{entry.entry_id}_{key}"` und `device_info` verwendet `(DOMAIN, entry.entry_id)`.
- `config_flow.py` — zeigt wie Konfiguration und Options-Flow gebaut sind (Voluptuous + `selector.EntitySelector`).

3) Konventionen & Patterns to follow
- Use `DataUpdateCoordinator` for polling and return a plain dict; platform entities read `self.coordinator.data[...]`.
- Persist small state/timers in `entry.options` (isoformat strings) and restore on coordinator init.
- Service calls: use `await self.hass.services.async_call(...)` from entity methods (no direct device calls).
- Async-first: alle I/O sind `async def`; use `dt_util` for datetimes.
- Translation keys: entities set `_attr_translation_key` and `translations/*.json` provide labels.

4) How to add a sensor / example
- Add an entry to the `entities` list in `sensor.py` (e.g. `PoolChemSensor(coordinator, "ph_val", "pH-Wert", None, "mdi:ph")`).
- Ensure `unique_id = f"{coordinator.entry.entry_id}_{key}"` so entities are stable across restarts.
- Populate the value by adding the computed key in `coordinator._async_update_data()` return dict.

5) Developer workflow (local HA dev)
- Install this folder as `config/custom_components/pool_controller` in your Home Assistant config.
- Restart Home Assistant and complete the Config Flow via UI (uses selectors shown in `config_flow.py`).
- Enable debug logging for `pool_controller` in `configuration.yaml` or UI to inspect coordinator logs and UpdateFailed messages.
- Check `home-assistant.log` for exceptions from coordinator and config flow.

6) Debugging tips for AI edits
- When changing coordinator logic, run a simulated update by reviewing `_async_update_data()` — ensure returned keys used by entities exist.
- If adding service calls, follow existing pattern: call domain `switch.turn_on`/`turn_off` with `entity_id` from `entry.data`.
- If changing persisted options, mirror parsing/serialization found in `coordinator.__init__` for `pause_until` / `quick_chlorine_until`.

7) Translations & metadata
- Update `translations/*.json` when adding translation keys used by `_attr_translation_key`.
- Bump `manifest.json` `version` when releasing logic changes.

8) What *not* to change
- Don't remove `PLATFORMS` or the `hass.data[DOMAIN][entry.entry_id]` storage pattern.
- Avoid blocking I/O in `coordinator._async_update_data()`; always raise `UpdateFailed` on unexpected errors.

Wenn unklar: frage, welche Datei oder welches Feature du ändern möchtest; ich kann dann präzise Beispiele oder einen Patch anbieten.
