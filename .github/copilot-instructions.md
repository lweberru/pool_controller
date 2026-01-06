# Copilot / AI Agent Hinweise — pool_controller

## Overview
Home Assistant custom integration for advanced pool/spa automation with calendar-driven heating, PV solar optimization, water quality monitoring, and automatic filtration cycles.

**Domain**: `pool_controller` | **Version**: 1.3.1 | **Type**: `local_polling`

---

## Architecture & Data Flow

### Core Pattern: DataUpdateCoordinator
```
ConfigEntry → PoolControllerDataCoordinator (30s polling) → coordinator.data dict → Platform Entities
```

**Key Files**:
- [__init__.py](custom_components/pool_controller/__init__.py) — Entry point (120 lines); creates coordinator, registers 6 services, loads 5 platforms
- [coordinator.py](custom_components/pool_controller/coordinator.py) — 322-line state machine; `_async_update_data()` returns dict with ~20 keys
- [const.py](custom_components/pool_controller/const.py) — 66 lines; 51 config keys with defaults (sensors, calendars, thresholds)
- [config_flow.py](custom_components/pool_controller/config_flow.py) — 128-line 5-step wizard using `selector.EntitySelector` for HA entity pickers

### State Machine Logic (coordinator.py)
The coordinator computes desired states in priority order:
1. **Frost protection** (outdoor < 3°C) → force main pump ON
2. **Quick chlorine** (5-min timer) → force main pump ON
3. **Bathing timer** (user-activated) → main ON, prevent turn-off
4. **Filter cycle** (auto-start based on `next_filter_start`) → respects quiet hours & PV
5. **Calendar events** (from `pool_calendar`) → auto-start bathing if event active
6. **PV surplus** (hysteresis: ON at 1000W, OFF at 500W) → main ON if surplus available

**Critical**: Main pump state changes are executed directly in `_async_update_data()` via `await self.hass.services.async_call("switch", "turn_on/off", ...)` to ensure physical switches follow logic.

---

## Persistence Pattern

Timers survive restarts by storing ISO datetime strings in `entry.options`:
```python
# Persist (coordinator.py ~L68-72)
new_opts = {**self.entry.options, "quick_chlorine_until": until.isoformat()}
await self.hass.config_entries.async_update_entry(self.entry, options=new_opts)

# Restore (coordinator.__init__ ~L18-38)
q = entry.options.get("quick_chlorine_until")
self.quick_chlorine_until = dt_util.parse_datetime(q) if q else None
```

**Persisted timers**: `pause_until`, `bathing_until`, `quick_chlorine_until`, `filter_until`, `next_filter_start`

---

## Platform Entity Patterns

### Adding a Sensor (sensor.py)
```python
# 1. Add to entities list in async_setup_entry (~L6-22)
PoolChemSensor(coordinator, "new_key", "Display Name", "unit", "mdi:icon")

# 2. Populate in coordinator._async_update_data() return dict (~L218)
return {
    "new_key": computed_value,
    # ... existing keys
}

# 3. Add translation to translations/de.json (and en/es/fr)
"entity": {
  "sensor": {
    "new_key": {"name": "Übersetzter Name"}
  }
}
```

**unique_id convention**: `f"{coordinator.entry.entry_id}_{key}"` for stable entity IDs across restarts.

**Sensor classes**:
- `PoolChemSensor` — Generic numeric sensors with custom units (pH, chlorine, etc.)
- `PoolTimeSensor` — Timestamp sensors using `SensorDeviceClass.TIMESTAMP` for timers
- `PoolStatusSensor` — Status sensor with translation_key for multi-state display

### Service Calls from Entities (switch.py ~L35)
```python
# ALWAYS call HA services indirectly; never touch hardware directly
await self.hass.services.async_call(
    "switch", "turn_on", 
    {"entity_id": self.coordinator.entry.data.get(CONF_MAIN_SWITCH)}
)
```

**Demo mode**: Check `entry.data.get(CONF_DEMO_MODE)` to skip physical switch calls during testing.

---

## Services & Buttons

**6 Services** registered in `__init__.py`:
- `start_pause` / `stop_pause` — Pause all automation (30-1440 min, validated via voluptuous schema)
- `start_bathing` / `stop_bathing` — Manual bathing sessions (default 60 min)
- `start_filter` / `stop_filter` — Manual filter cycles (default 30 min)

**13 Button entities** (button.py): Quick actions that call coordinator methods + refresh:
- **Chlorine**: `QuickChlorineButton` (5min)
- **Pause**: 30/60/120min + Stop (calls `activate_pause()`)
- **Bathing**: 30/60/120min + Stop (calls `activate_bathing()` / `deactivate_bathing()`)
- **Filter**: 30/60/120min + Stop (calls `activate_filter()` / `deactivate_filter()`)

**Pattern**: All buttons extend `PoolButton`, set `_attr_translation_key`, call coordinator method, then `await coordinator.async_request_refresh()` to trigger immediate state update.

---

## Multi-Step Config Flow

5-step wizard with back navigation (config_flow.py, 128 lines):
1. **user**: Pool name, water volume (int), demo mode toggle (bool)
2. **switches**: Main/aux switches, power sensors (EntitySelector with domain filters)
3. **water_quality**: Temp sensors (required), pH/chlorine/salt/TDS sensors (optional)
4. **calendars**: Pool calendar (events), holiday calendar, quiet hours (weekday/weekend time strings)
5. **pv**: PV surplus sensor + ON/OFF thresholds (default 1000W/500W)

**Navigation**: Each step checks `user_input.get("back")` to return to previous step. Uses `selector.EntitySelector` with domain/device_class filters for type-safe entity selection.

**Config storage**: All settings stored in `entry.data`, timers stored/restored via `entry.options` (see Persistence Pattern).

---

## Developer Workflow

### Local Development
```bash
# Symlink into HA config
ln -s $(pwd)/custom_components/pool_controller ~/.homeassistant/custom_components/

# Enable debug logging (configuration.yaml)
logger:
  logs:
    custom_components.pool_controller: debug

# Restart HA, then add integration via UI
```

### Testing Changes
1. Modify coordinator logic → verify returned keys match entity expectations
2. Change entity → check `unique_id` stability and `device_info` consistency
3. Add service → update `services.yaml` + register handler in `__init__.py`
4. Update translations → edit all 4 language files (de/en/es/fr)
5. Bump `manifest.json` version before release

### Common Pitfalls
- ❌ Blocking I/O in `_async_update_data()` → use `async def` + `await`
- ❌ Forgetting to call `coordinator.async_request_refresh()` after timer changes
- ❌ Hardcoding entity IDs → always read from `entry.data.get(CONF_*)`
- ❌ Not checking demo mode → physical switches will toggle during tests

---

## Integration Points

### External Dependencies
- **Calendar integration** (HA core) — `calendar.get_events` service for event queries
- **Entity selectors** — Config flow uses `selector.EntitySelector` for type-safe entity pickers
- **dt_util** (HA util) — `dt_util.now()`, `parse_datetime()`, `parse_time()` for timezone-aware ops

### Optional Hardware (ESP32 + Blueriiot)
See `esphome-blueriiot-example.yaml` for ESP32-S3 + BLE proxy config reading Blue Connect GO sensor.

### Frontend Dashboard
Separate repo: `lweberru/pool_controller_dashboard_frontend` (HACS Plugin, card type `custom:pc-pool-controller`)

---

## Translation System

Uses `_attr_translation_key` + `translations/*.json`:
```python
# Entity (sensor.py)
_attr_translation_key = "ph_val"

# Translation (translations/de.json)
"entity": {
  "sensor": {
    "ph_val": {"name": "pH-Wert"}
  }
}
```

**Languages**: de (primary), en, es, fr — keep all 4 in sync when adding entities.

---

## Critical Constraints

**DO NOT**:
- Remove `PLATFORMS` list or `hass.data[DOMAIN][entry.entry_id]` storage
- Use synchronous I/O in coordinator (blocks event loop)
- Modify `unique_id` format (breaks entity registry)
- Skip `raise UpdateFailed(err)` on coordinator errors

**ALWAYS**:
- Use `dt_util` for datetime operations (timezone-aware)
- Call `async_request_refresh()` after coordinator state changes
- Preserve demo mode checks in switch on/off methods
- Update all translation files when adding entities

---

Wenn unklar: frage, welche Datei oder welches Feature du ändern möchtest; ich kann dann präzise Beispiele oder einen Patch anbieten.
