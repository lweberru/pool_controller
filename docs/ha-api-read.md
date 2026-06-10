# Home Assistant API Helper Script

**English** | [Deutsch](de/ha-api-read.md)

[← Back to README](../README.md)

## Purpose

`tools/ha_api_read.py` is a helper to inspect Home Assistant REST API data and optionally call services during development and troubleshooting.

Typical use cases:

- Verify current entity states without opening multiple HA views.
- Pull short history windows for correlation analysis.
- Inspect available services and raw API endpoints.
- Speed up debugging sessions between backend and frontend changes.

The script supports `GET` requests and explicit service calls (`POST /api/services/...`).

## Credentials and Configuration

Credentials can be provided in this order:

1. `--config path/to/file.json`
2. Environment variables `HA_URL` and `HA_TOKEN`
3. Local default file `tools/.ha_api.local.json`

Example config file:

```json
{
  "ha_url": "https://home.example.local/",
  "ha_token": "YOUR_LONG_LIVED_ACCESS_TOKEN"
}
```

For local developer safety:

- Keep the token file out of git.
- Rotate tokens if they were exposed.

## Global Options

- `--timeout <seconds>`: HTTP timeout (default `20`)
- `--compact`: one-line compact JSON output
- `--insecure`: disable TLS certificate validation (use only in trusted local setups)

## Commands

### states

Read `/api/states` with optional filters.

```bash
python3 tools/ha_api_read.py states
python3 tools/ha_api_read.py --compact states --domain sensor --contains whirlpool
python3 tools/ha_api_read.py --compact states --contains alkal --limit 50
```

### state

Read one entity from `/api/states/<entity_id>`.

```bash
python3 tools/ha_api_read.py state climate.whirlpool
```

### history

Read entity history from `/api/history/period`.

```bash
python3 tools/ha_api_read.py history sensor.garten_whirlpool_alkalinitats_aktion --hours 24
python3 tools/ha_api_read.py --compact history sensor.garten_whirlpool_alkalinitats_status --hours 24 --minimal --no-attributes
python3 tools/ha_api_read.py --compact history sensor.garten_whirlpool_geschatzte_alkalinitat --hours 12 --significant-only
```

### services

Read `/api/services`.

```bash
python3 tools/ha_api_read.py services
```

### get

Read any GET API path.

```bash
python3 tools/ha_api_read.py get /api/config
python3 tools/ha_api_read.py get /api/logbook --query entity=sensor.garten_whirlpool_alkalinitats_aktion
```

### call

Call a Home Assistant service directly.

```bash
python3 tools/ha_api_read.py call pool_controller set_options --target-entity climate.whirlpool --data enable_dynamic_target=true --data dynamic_target_weather_entity=weather.openweathermap
```

### apply-dynamic-target-defaults

Convenience command to apply pool_controller dynamic-target defaults to one pool.

```bash
python3 tools/ha_api_read.py apply-dynamic-target-defaults climate.whirlpool --weather-entity weather.openweathermap --enable
```

## Practical Workflow

For recommendation analysis (for example `measure_first`), compare these in the same time window:

1. `sensor.<pool>_alkalinitats_aktion` history
2. `sensor.<pool>_alkalinitats_status` history
3. `sensor.<pool>_geschatzte_alkalinitat` history
4. `climate.<pool>` history

This quickly reveals whether changes came from restart windows, unavailable states, or normal runtime transitions.

## Notes on SSL

If your HA endpoint uses a self-signed or incomplete certificate chain, requests can fail with `CERTIFICATE_VERIFY_FAILED`.

In this case, you can use:

```bash
python3 tools/ha_api_read.py --insecure states --contains whirlpool
```

Use `--insecure` only in trusted environments.

## Error Handling

The script returns clear stderr errors for:

- Missing credentials
- HTTP errors with response body
- Connection failures
- Invalid JSON responses

This makes it suitable for quick shell pipelines and diagnostics.
