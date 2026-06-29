#!/usr/bin/env python3
"""Home Assistant REST API helper.

Usage examples:
  python3 tools/ha_api_read.py states
  python3 tools/ha_api_read.py state climate.pool
  python3 tools/ha_api_read.py history sensor.pool_temp --hours 24
  python3 tools/ha_api_read.py services
    python3 tools/ha_api_read.py call pool_controller set_dynamic_target --target-entity climate.whirlpool --data enabled=true --data weather_entity=weather.openweathermap
    python3 tools/ha_api_read.py apply-dynamic-target-defaults climate.whirlpool --weather-entity weather.openweathermap
  python3 tools/ha_api_read.py get /api/config

Credentials and URL can be provided via:
  1) --config path/to/file.json
  2) Environment variables: HA_URL, HA_TOKEN
  3) Local default config file: tools/.ha_api.local.json

The script supports GET requests and explicit service calls (POST).
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _load_json_file(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Config JSON must be an object")
        return data
    except FileNotFoundError:
        return {}


def _resolve_credentials(config_path: str | None) -> tuple[str, str, Path | None]:
    script_dir = Path(__file__).resolve().parent
    default_config = script_dir / ".ha_api.local.json"

    cfg: dict = {}
    used_path: Path | None = None

    if config_path:
        used_path = Path(config_path).expanduser().resolve()
        cfg = _load_json_file(used_path)
    elif default_config.exists():
        used_path = default_config
        cfg = _load_json_file(default_config)

    ha_url = (
        os.getenv("HA_URL")
        or cfg.get("ha_url")
        or cfg.get("url")
        or ""
    ).strip()
    ha_token = (
        os.getenv("HA_TOKEN")
        or cfg.get("ha_token")
        or cfg.get("token")
        or ""
    ).strip()

    if not ha_url or not ha_token:
        source = f" (checked config: {used_path})" if used_path else ""
        raise RuntimeError(
            "Missing Home Assistant credentials. Set HA_URL and HA_TOKEN, "
            "or provide --config, or create tools/.ha_api.local.json" + source
        )

    return ha_url.rstrip("/"), ha_token, used_path


def _request_json(
    ha_url: str,
    token: str,
    path: str,
    timeout: int = 20,
    insecure: bool = False,
    method: str = "GET",
    payload: object | None = None,
) -> object:
    if not path.startswith("/"):
        path = "/" + path
    url = ha_url + path

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        method=method.upper(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        ssl_ctx = ssl._create_unverified_context() if insecure else None
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            raw = resp.read().decode("utf-8")
            if not raw.strip():
                return {"ok": True, "status": resp.status}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {url}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error for {url}: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from {url}: {e}") from e


def _print_json(data: object, compact: bool) -> None:
    if compact:
        print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False))


def _cmd_states(args: argparse.Namespace, ha_url: str, token: str) -> None:
    data = _request_json(ha_url, token, "/api/states", timeout=args.timeout, insecure=args.insecure)
    if not isinstance(data, list):
        _print_json(data, args.compact)
        return

    filtered = data
    if args.domain:
        dom = args.domain.lower() + "."
        filtered = [x for x in filtered if str(x.get("entity_id", "")).lower().startswith(dom)]
    if args.contains:
        q = args.contains.lower()
        filtered = [x for x in filtered if q in str(x.get("entity_id", "")).lower()]

    if args.limit and args.limit > 0:
        filtered = filtered[: args.limit]

    _print_json(filtered, args.compact)


def _cmd_state(args: argparse.Namespace, ha_url: str, token: str) -> None:
    path = "/api/states/" + urllib.parse.quote(args.entity_id, safe="._")
    data = _request_json(ha_url, token, path, timeout=args.timeout, insecure=args.insecure)
    _print_json(data, args.compact)


def _cmd_history(args: argparse.Namespace, ha_url: str, token: str) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=args.hours)
    start_iso = start.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    query = {
        "filter_entity_id": args.entity_id,
        "minimal_response": "1" if args.minimal else "0",
        "no_attributes": "1" if args.no_attributes else "0",
        "significant_changes_only": "1" if args.significant_only else "0",
    }
    query_str = urllib.parse.urlencode(query)
    path = f"/api/history/period/{urllib.parse.quote(start_iso, safe=':-TZ')}?{query_str}"

    data = _request_json(ha_url, token, path, timeout=args.timeout, insecure=args.insecure)
    _print_json(data, args.compact)


def _cmd_services(args: argparse.Namespace, ha_url: str, token: str) -> None:
    data = _request_json(ha_url, token, "/api/services", timeout=args.timeout, insecure=args.insecure)
    _print_json(data, args.compact)


def _cmd_get(args: argparse.Namespace, ha_url: str, token: str) -> None:
    path = args.path
    if args.query:
        sep = "&" if "?" in path else "?"
        path = path + sep + "&".join(args.query)
    data = _request_json(ha_url, token, path, timeout=args.timeout, insecure=args.insecure)
    _print_json(data, args.compact)


def _parse_kv_pairs(items: list[str] | None) -> dict:
    out: dict = {}
    if not items:
        return out

    for item in items:
        if "=" not in item:
            raise RuntimeError(f"Invalid --data item '{item}', expected key=value")
        key, raw = item.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if not key:
            raise RuntimeError(f"Invalid --data item '{item}', empty key")

        low = raw.lower()
        if low == "true":
            value: object = True
        elif low == "false":
            value = False
        elif low == "null":
            value = None
        else:
            # Allow numeric values and JSON payload fragments.
            try:
                if raw.startswith("{") or raw.startswith("["):
                    value = json.loads(raw)
                elif "." in raw:
                    value = float(raw)
                else:
                    value = int(raw)
            except Exception:
                value = raw
        out[key] = value
    return out


def _cmd_call(args: argparse.Namespace, ha_url: str, token: str) -> None:
    payload = _parse_kv_pairs(args.data)
    if args.target_entity:
        payload["target"] = {"entity_id": args.target_entity}

    path = "/api/services/" + urllib.parse.quote(args.domain, safe="") + "/" + urllib.parse.quote(args.service, safe="")
    data = _request_json(
        ha_url,
        token,
        path,
        timeout=args.timeout,
        insecure=args.insecure,
        method="POST",
        payload=payload,
    )
    _print_json(data, args.compact)


def _cmd_apply_dynamic_target_defaults(args: argparse.Namespace, ha_url: str, token: str) -> None:
    if args.enable and args.disable:
        raise RuntimeError("Use either --enable or --disable, not both")

    payload = {
        "target": {"entity_id": args.entity_id},
        "weather_entity": args.weather_entity,
        "winter_offset": 4.0,
        "spring_offset": 2.0,
        "summer_offset": -4.5,
        "autumn_offset": 1.0,
        "min_offset": -6.5,
        "max_offset": 5.0,
        "weather_max_offset": 3.0,
        "weight_temp": 0.55,
        "weight_feels_like": 0.30,
        "weight_wind": 0.15,
        "weight_uv": 0.10,
        "weight_cloud": 0.10,
        "weight_forecast": 0.10,
        "ema_alpha": 0.20,
        "max_step_per_hour": 1.0,
    }
    if args.enable:
        payload["enabled"] = True
    if args.disable:
        payload["enabled"] = False

    mapped_payload = {
        "target": payload["target"],
        "enable_dynamic_target": payload.get("enabled"),
        "dynamic_target_weather_entity": payload["weather_entity"],
        "dynamic_target_winter_offset": payload["winter_offset"],
        "dynamic_target_spring_offset": payload["spring_offset"],
        "dynamic_target_summer_offset": payload["summer_offset"],
        "dynamic_target_autumn_offset": payload["autumn_offset"],
        "dynamic_target_min_offset": payload["min_offset"],
        "dynamic_target_max_offset": payload["max_offset"],
        "dynamic_target_weather_max_offset": payload["weather_max_offset"],
        "dynamic_target_weather_weight_temp": payload["weight_temp"],
        "dynamic_target_weather_weight_feels_like": payload["weight_feels_like"],
        "dynamic_target_weather_weight_wind": payload["weight_wind"],
        "dynamic_target_weather_weight_uv": payload["weight_uv"],
        "dynamic_target_weather_weight_cloud": payload["weight_cloud"],
        "dynamic_target_weather_weight_forecast": payload["weight_forecast"],
        "dynamic_target_ema_alpha": payload["ema_alpha"],
        "dynamic_target_max_step_per_hour": payload["max_step_per_hour"],
    }
    if mapped_payload["enable_dynamic_target"] is None:
        mapped_payload.pop("enable_dynamic_target", None)

    data = _request_json(
        ha_url,
        token,
        "/api/services/pool_controller/set_options",
        timeout=args.timeout,
        insecure=args.insecure,
        method="POST",
        payload=mapped_payload,
    )
    _print_json(data, args.compact)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Home Assistant API helper")
    p.add_argument("--config", help="Path to JSON config file with ha_url and ha_token")
    p.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds (default: 20)")
    p.add_argument("--compact", action="store_true", help="Print compact JSON")
    p.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification")

    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("states", help="Read /api/states with optional filters")
    ps.add_argument("--domain", help="Filter by entity domain, e.g. sensor")
    ps.add_argument("--contains", help="Filter entity_id substring")
    ps.add_argument("--limit", type=int, help="Limit output rows")

    pe = sub.add_parser("state", help="Read one entity from /api/states/<entity_id>")
    pe.add_argument("entity_id", help="Entity ID, e.g. climate.pool")

    ph = sub.add_parser("history", help="Read entity history from /api/history/period")
    ph.add_argument("entity_id", help="Entity ID")
    ph.add_argument("--hours", type=float, default=24.0, help="Lookback window in hours (default: 24)")
    ph.add_argument("--minimal", action="store_true", help="Use minimal_response=1")
    ph.add_argument("--no-attributes", action="store_true", help="Use no_attributes=1")
    ph.add_argument("--significant-only", action="store_true", help="Use significant_changes_only=1")

    sub.add_parser("services", help="Read /api/services")

    pg = sub.add_parser("get", help="Read any GET API path")
    pg.add_argument("path", help="API path, e.g. /api/config")
    pg.add_argument(
        "--query",
        action="append",
        help="Query string item key=value. Can be repeated.",
    )

    pc = sub.add_parser("call", help="Call a Home Assistant service (POST /api/services/<domain>/<service>)")
    pc.add_argument("domain", help="Service domain, e.g. pool_controller")
    pc.add_argument("service", help="Service name, e.g. set_dynamic_target")
    pc.add_argument("--target-entity", help="Optional target entity_id (mapped to payload.target.entity_id)")
    pc.add_argument(
        "--data",
        action="append",
        help="Service data item as key=value. Can be repeated.",
    )

    pd = sub.add_parser(
        "apply-dynamic-target-defaults",
        help="Apply pool_controller dynamic-target defaults to one climate entity",
    )
    pd.add_argument("entity_id", help="Target climate entity_id, e.g. climate.whirlpool")
    pd.add_argument(
        "--weather-entity",
        default="weather.openweathermap",
        help="Weather entity used for dynamic target (default: weather.openweathermap)",
    )
    pd.add_argument("--enable", action="store_true", help="Enable dynamic target while applying defaults")
    pd.add_argument("--disable", action="store_true", help="Disable dynamic target while applying defaults")

    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        ha_url, token, _used = _resolve_credentials(args.config)

        if args.command == "states":
            _cmd_states(args, ha_url, token)
        elif args.command == "state":
            _cmd_state(args, ha_url, token)
        elif args.command == "history":
            _cmd_history(args, ha_url, token)
        elif args.command == "services":
            _cmd_services(args, ha_url, token)
        elif args.command == "get":
            _cmd_get(args, ha_url, token)
        elif args.command == "call":
            _cmd_call(args, ha_url, token)
        elif args.command == "apply-dynamic-target-defaults":
            _cmd_apply_dynamic_target_defaults(args, ha_url, token)
        else:
            parser.error(f"Unknown command: {args.command}")
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
