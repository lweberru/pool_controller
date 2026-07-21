#!/usr/bin/env python3
"""Home Assistant REST API helper.

Usage examples:
  python3 tools/ha_api_read.py states
    python3 tools/ha_api_read.py states --compact --contains whirlpool
  python3 tools/ha_api_read.py state climate.pool
    python3 tools/ha_api_read.py pool --entity-id climate.whirlpool
    python3 tools/ha_api_read.py pool --device-id 0123456789abcdef
    python3 tools/ha_api_read.py pool-config --entity-id climate.whirlpool
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
import base64
import json
import os
import re
import socket
import ssl
import struct
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


SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|passwd|credential|api[_-]?key)", re.IGNORECASE)
_CERT_FALLBACK_WARNED = False


def _resolve_credentials(config_path: str | None, url_override: str | None = None, use_local_url: bool = False) -> tuple[str, str, Path | None, bool]:
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

    configured_local_url = (
        os.getenv("HA_LOCAL_URL")
        or cfg.get("ha_local_url")
        or cfg.get("local_url")
        or ""
    ).strip()
    configured_url = (
        os.getenv("HA_URL")
        or cfg.get("ha_url")
        or cfg.get("url")
        or ""
    ).strip()
    ha_url = (url_override or (configured_local_url if use_local_url else configured_url)).strip()
    ha_token = (
        os.getenv("HA_TOKEN")
        or cfg.get("ha_token")
        or cfg.get("token")
        or ""
    ).strip()
    default_insecure = str(os.getenv("HA_INSECURE", "")).lower() in {"1", "true", "yes", "on"}
    default_insecure = bool(cfg.get("insecure", default_insecure))

    if not ha_url or not ha_token:
        source = f" (checked config: {used_path})" if used_path else ""
        raise RuntimeError(
            "Missing Home Assistant credentials. Set HA_URL and HA_TOKEN, "
            "or provide --config, or create tools/.ha_api.local.json" + source
        )
    if use_local_url and not configured_local_url and not url_override:
        raise RuntimeError("--local was requested but no HA_LOCAL_URL/local_url/ha_local_url is configured")

    return ha_url.rstrip("/"), ha_token, used_path, default_insecure


def _is_cert_error(err: urllib.error.URLError) -> bool:
    reason = getattr(err, "reason", None)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return True
    return "CERTIFICATE_VERIFY_FAILED" in str(err)


def _request_json(
    ha_url: str,
    token: str,
    path: str,
    timeout: int = 20,
    insecure: bool = False,
    method: str = "GET",
    payload: object | None = None,
) -> object:
    global _CERT_FALLBACK_WARNED
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
        try:
            resp_ctx = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        except urllib.error.URLError as e:
            if not insecure and _is_cert_error(e):
                if not _CERT_FALLBACK_WARNED:
                    print("WARNING: TLS certificate verification failed; retrying with --insecure", file=sys.stderr)
                    _CERT_FALLBACK_WARNED = True
                resp_ctx = urllib.request.urlopen(req, timeout=timeout, context=ssl._create_unverified_context())
            else:
                raise
        with resp_ctx as resp:
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


class _HomeAssistantWebSocket:
    def __init__(self, ha_url: str, token: str, timeout: int, insecure: bool) -> None:
        self.ha_url = ha_url
        self.token = token
        self.timeout = timeout
        self.insecure = insecure
        self.sock: socket.socket | ssl.SSLSocket | None = None
        self.buffer = b""
        self.next_id = 1

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        if self.sock:
            self.sock.close()

    def _connect(self) -> None:
        global _CERT_FALLBACK_WARNED
        parsed = urllib.parse.urlparse(self.ha_url)
        host = parsed.hostname
        if not host:
            raise RuntimeError(f"Invalid HA_URL: {self.ha_url}")
        secure = parsed.scheme == "https"
        port = parsed.port or (443 if secure else 80)
        base_path = parsed.path.rstrip("/") if parsed.path else ""
        path = f"{base_path}/api/websocket"

        raw = socket.create_connection((host, port), timeout=self.timeout)
        if secure:
            try:
                ctx = ssl._create_unverified_context() if self.insecure else ssl.create_default_context()
                raw = ctx.wrap_socket(raw, server_hostname=host)
            except ssl.SSLCertVerificationError:
                raw.close()
                if not _CERT_FALLBACK_WARNED:
                    print("WARNING: TLS certificate verification failed; retrying with --insecure", file=sys.stderr)
                    _CERT_FALLBACK_WARNED = True
                raw = socket.create_connection((host, port), timeout=self.timeout)
                raw = ssl._create_unverified_context().wrap_socket(raw, server_hostname=host)
        self.sock = raw

        key = base64.b64encode(os.urandom(16)).decode()
        request = "\r\n".join([
            f"GET {path} HTTP/1.1",
            f"Host: {host}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
            "User-Agent: Mozilla/5.0",
            "Sec-WebSocket-Protocol: home-assistant",
            "",
            "",
        ])
        self.sock.sendall(request.encode("ascii"))
        raw_response = b""
        while b"\r\n\r\n" not in raw_response:
            raw_response += self.sock.recv(4096)
        header_blob, self.buffer = raw_response.split(b"\r\n\r\n", 1)
        status_line = header_blob.decode("iso-8859-1", errors="replace").split("\r\n", 1)[0]
        if " 101 " not in status_line:
            raise RuntimeError(f"WebSocket handshake failed: {status_line}")

        hello = self.receive()
        if hello.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected WebSocket hello: {hello}")
        self.send({"type": "auth", "access_token": self.token})
        auth = self.receive()
        if auth.get("type") != "auth_ok":
            raise RuntimeError(f"Home Assistant WebSocket auth failed: {auth}")

    def _read_exact(self, count: int) -> bytes:
        if not self.sock:
            raise RuntimeError("WebSocket is not connected")
        while len(self.buffer) < count:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket closed unexpectedly")
            self.buffer += chunk
        data, self.buffer = self.buffer[:count], self.buffer[count:]
        return data

    def send(self, payload: dict, opcode: int = 1) -> None:
        if not self.sock:
            raise RuntimeError("WebSocket is not connected")
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        mask = os.urandom(4)
        frame = bytearray([0x80 | opcode])
        length = len(data)
        if length < 126:
            frame.append(0x80 | length)
        elif length < 65536:
            frame.append(0x80 | 126)
            frame.extend(struct.pack("!H", length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack("!Q", length))
        frame.extend(mask)
        frame.extend(bytes(byte ^ mask[index % 4] for index, byte in enumerate(data)))
        self.sock.sendall(frame)

    def receive(self) -> dict:
        header = self._read_exact(2)
        first, second = header
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask = self._read_exact(4) if second & 0x80 else b""
        payload = self._read_exact(length) if length else b""
        if mask:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 8:
            raise RuntimeError(f"WebSocket closed by server: {payload!r}")
        if opcode == 9:
            self.send({}, opcode=10)
            return self.receive()
        if opcode != 1:
            return self.receive()
        return json.loads(payload.decode("utf-8"))

    def command(self, command_type: str, **payload) -> object:
        command_id = self.next_id
        self.next_id += 1
        self.send({"id": command_id, "type": command_type, **payload})
        while True:
            message = self.receive()
            if message.get("id") != command_id:
                continue
            if not message.get("success", False):
                raise RuntimeError(f"WebSocket command {command_type!r} failed: {message.get('error')}")
            return message.get("result")


def _ws_cache(args: argparse.Namespace, ha_url: str, token: str, key: str, command_type: str) -> list[dict]:
    cache_name = f"_ws_{key}"
    cached = getattr(args, cache_name, None)
    if cached is not None:
        return cached
    with _HomeAssistantWebSocket(ha_url, token, args.timeout, args.insecure) as ws:
        result = ws.command(command_type)
    if not isinstance(result, list):
        result = []
    setattr(args, cache_name, result)
    return result


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "***REDACTED***" if SENSITIVE_KEY_RE.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _service_response(
    args: argparse.Namespace,
    ha_url: str,
    token: str,
    domain: str,
    service: str,
    target: dict | None = None,
    service_data: dict | None = None,
) -> object:
    payload = {
        "domain": domain,
        "service": service,
        "target": target or {},
        "service_data": service_data or {},
        "return_response": True,
    }
    with _HomeAssistantWebSocket(ha_url, token, args.timeout, args.insecure) as ws:
        result = ws.command("call_service", **payload)
    if isinstance(result, dict) and "response" in result:
        return result["response"]
    return result


def _entity_id_matches_query(state: dict, query: str) -> bool:
    q = query.lower()
    return q in str(state.get("entity_id", "")).lower() or q in str(state.get("attributes", {}).get("friendly_name", "")).lower()


def _looks_like_pool_climate(state: dict, name_query: str | None = None) -> bool:
    if not str(state.get("entity_id", "")).startswith("climate."):
        return False
    if name_query and not _entity_id_matches_query(state, name_query):
        return False
    attrs = state.get("attributes", {}) if isinstance(state.get("attributes"), dict) else {}
    haystack = " ".join([
        str(state.get("entity_id", "")),
        str(attrs.get("friendly_name", "")),
        " ".join(str(mode) for mode in attrs.get("preset_modes", []) if mode is not None),
    ]).lower()
    return any(token in haystack for token in ("pool", "whirlpool", "spa", "baden", "chloren", "filtern"))


def _find_registry_entities(args: argparse.Namespace, ha_url: str, token: str, device_id: str | None = None, entity_id: str | None = None) -> list[dict]:
    entities = _ws_cache(args, ha_url, token, "entity_registry", "config/entity_registry/list")
    if entity_id:
        return [entity for entity in entities if entity.get("entity_id") == entity_id]
    if device_id:
        return [entity for entity in entities if entity.get("device_id") == device_id]
    return []


def _find_pool_climate(args: argparse.Namespace, ha_url: str, token: str) -> dict | None:
    if getattr(args, "entity_id", None):
        return _request_json(ha_url, token, "/api/states/" + urllib.parse.quote(args.entity_id, safe="._"), timeout=args.timeout, insecure=args.insecure)

    if getattr(args, "device_id", None):
        for entity in _find_registry_entities(args, ha_url, token, device_id=args.device_id):
            entity_id = str(entity.get("entity_id", ""))
            if entity_id.startswith("climate."):
                return _request_json(ha_url, token, "/api/states/" + urllib.parse.quote(entity_id, safe="._"), timeout=args.timeout, insecure=args.insecure)

    states = _request_json(ha_url, token, "/api/states", timeout=args.timeout, insecure=args.insecure)
    if not isinstance(states, list):
        return None
    candidates = [state for state in states if _looks_like_pool_climate(state, getattr(args, "name", None))]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        return sorted(candidates, key=lambda state: str(state.get("entity_id", "")))[0]
    return None


def _related_entities_from_registry(args: argparse.Namespace, ha_url: str, token: str, climate_entity_id: str) -> list[str]:
    registry_matches = _find_registry_entities(args, ha_url, token, entity_id=climate_entity_id)
    device_ids = {entity.get("device_id") for entity in registry_matches if entity.get("device_id")}
    config_entry_ids = set()
    for entity in registry_matches:
        config_entry_id = entity.get("config_entry_id")
        if config_entry_id:
            config_entry_ids.add(config_entry_id)
        config_entry_ids.update(entity.get("config_entry_ids") or [])

    related = []
    for entity in _ws_cache(args, ha_url, token, "entity_registry", "config/entity_registry/list"):
        entity_config_ids = set(entity.get("config_entry_ids") or [])
        if entity.get("config_entry_id"):
            entity_config_ids.add(entity.get("config_entry_id"))
        if entity.get("device_id") in device_ids or entity_config_ids.intersection(config_entry_ids):
            entity_id = entity.get("entity_id")
            if entity_id:
                related.append(entity_id)
    return sorted(set(related))


def _pool_config(args: argparse.Namespace, ha_url: str, token: str, climate_entity_id: str | None = None) -> dict:
    target = {}
    if climate_entity_id:
        target["entity_id"] = [climate_entity_id]
    elif getattr(args, "device_id", None):
        target["device_id"] = [args.device_id]

    if target:
        try:
            response = _service_response(args, ha_url, token, "pool_controller", "get_options", target=target)
            if isinstance(response, dict):
                return {
                    "source": "pool_controller.get_options",
                    "matched_config_entries": [_redact(response)],
                    "note": None,
                }
        except Exception as exc:
            service_error = str(exc)
    else:
        service_error = "No target entity_id/device_id resolved for pool_controller.get_options."

    config_entry_ids = set()
    if getattr(args, "device_id", None):
        for entity in _find_registry_entities(args, ha_url, token, device_id=args.device_id):
            if entity.get("config_entry_id"):
                config_entry_ids.add(entity.get("config_entry_id"))
            config_entry_ids.update(entity.get("config_entry_ids") or [])
    if climate_entity_id:
        for entity in _find_registry_entities(args, ha_url, token, entity_id=climate_entity_id):
            if entity.get("config_entry_id"):
                config_entry_ids.add(entity.get("config_entry_id"))
            config_entry_ids.update(entity.get("config_entry_ids") or [])

    entries = _ws_cache(args, ha_url, token, "config_entries", "config_entries/get")
    matches = []
    for entry in entries:
        if entry.get("domain") != "pool_controller":
            continue
        if config_entry_ids and entry.get("entry_id") not in config_entry_ids:
            continue
        matches.append({
            "entry_id": entry.get("entry_id"),
            "title": entry.get("title"),
            "domain": entry.get("domain"),
            "data": _redact(entry.get("data", {})),
            "options": _redact(entry.get("options", {})),
        })

    return {
        "source": "home_assistant_websocket_metadata",
        "matched_config_entries": matches,
        "note": (
            "pool_controller.get_options is not available on the remote instance yet; "
            "showing HA config-entry metadata only. " + service_error
        ) if matches else "No remote pool_controller config entry matched the selector. " + service_error,
    }


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


def _state_summary(state: dict, full: bool = False) -> dict:
    if full:
        return state
    attrs = state.get("attributes", {}) if isinstance(state.get("attributes"), dict) else {}
    keep_attrs = {}
    for key in (
        "friendly_name",
        "unit_of_measurement",
        "device_class",
        "current_temperature",
        "temperature",
        "preset_mode",
        "hvac_action",
        "supported_features",
    ):
        if key in attrs:
            keep_attrs[key] = attrs[key]
    return {
        "entity_id": state.get("entity_id"),
        "state": state.get("state"),
        "attributes": keep_attrs,
        "last_updated": state.get("last_updated"),
    }


def _cmd_pool(args: argparse.Namespace, ha_url: str, token: str) -> None:
    climate = _find_pool_climate(args, ha_url, token)
    if not isinstance(climate, dict) or not climate.get("entity_id"):
        states = _request_json(ha_url, token, "/api/states", timeout=args.timeout, insecure=args.insecure)
        candidates = []
        if isinstance(states, list):
            candidates = [_state_summary(state) for state in states if _looks_like_pool_climate(state, getattr(args, "name", None))]
        _print_json({"error": "No pool climate entity found", "candidates": candidates}, args.compact)
        return

    climate_entity_id = str(climate["entity_id"])
    all_states = _request_json(ha_url, token, "/api/states", timeout=args.timeout, insecure=args.insecure)
    if not isinstance(all_states, list):
        all_states = []

    related_ids = set(_related_entities_from_registry(args, ha_url, token, climate_entity_id))
    object_token = climate_entity_id.split(".", 1)[-1]
    friendly_name = str(climate.get("attributes", {}).get("friendly_name", ""))
    tokens = {object_token.lower()}
    tokens.update(token.lower() for token in re.split(r"\W+", friendly_name) if len(token) >= 4)

    related_states = []
    for state in all_states:
        entity_id = str(state.get("entity_id", ""))
        if entity_id == climate_entity_id or entity_id in related_ids:
            related_states.append(state)
            continue
        haystack = " ".join([
            entity_id,
            str(state.get("attributes", {}).get("friendly_name", "")),
        ]).lower()
        if any(token and token in haystack for token in tokens):
            related_states.append(state)

    weather_states = [state for state in all_states if str(state.get("entity_id", "")).startswith("weather.")]

    dynamic_keys = (
        "target_temperature_base",
        "target_temperature_effective",
        "target_offset",
        "saison_offset",
        "wetter_offset",
        "dynamisches_zielprofil",
        "target_temp_base",
        "target_temp_effective",
        "target_temp_weather_offset",
        "dynamic_target_profile",
    )
    dynamic_entities = [
        state for state in related_states
        if any(key in str(state.get("entity_id", "")).lower() for key in dynamic_keys)
    ]

    output = {
        "pool": _state_summary(climate, args.full),
        "config": _pool_config(args, ha_url, token, climate_entity_id),
        "dynamic_target": [_state_summary(state, args.full) for state in sorted(dynamic_entities, key=lambda item: str(item.get("entity_id", "")))],
        "weather": [_state_summary(state, args.full) for state in sorted(weather_states, key=lambda item: str(item.get("entity_id", "")))],
        "related_entities": [_state_summary(state, args.full) for state in sorted(related_states, key=lambda item: str(item.get("entity_id", "")))],
    }
    _print_json(output, args.compact)


def _cmd_pool_config(args: argparse.Namespace, ha_url: str, token: str) -> None:
    climate_entity_id = getattr(args, "entity_id", None)
    if not climate_entity_id:
        climate = _find_pool_climate(args, ha_url, token)
        if isinstance(climate, dict):
            climate_entity_id = climate.get("entity_id")
    _print_json(_pool_config(args, ha_url, token, str(climate_entity_id) if climate_entity_id else None), args.compact)


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
        "winter_offset": 2.0,
        "spring_offset": 1.0,
        "summer_offset": -1.5,
        "autumn_offset": 0.5,
        "min_offset": -5.0,
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


def _add_pool_selector_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--entity-id", help="Pool climate entity_id, e.g. climate.whirlpool")
    parser.add_argument("--device-id", help="Home Assistant device_id from the remote entity registry")
    parser.add_argument("--name", default="whirlpool", help="Pool name search fallback (default: whirlpool)")


def _global_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--config", default=argparse.SUPPRESS, help="Path to JSON config file with ha_url and ha_token")
    parent.add_argument("--url", default=argparse.SUPPRESS, help="Override Home Assistant URL for this command")
    parent.add_argument("--local", action="store_true", default=argparse.SUPPRESS, help="Use ha_local_url/local_url from config or HA_LOCAL_URL")
    parent.add_argument("--timeout", type=int, default=argparse.SUPPRESS, help="HTTP timeout in seconds (default: 20)")
    parent.add_argument("--compact", action="store_true", default=argparse.SUPPRESS, help="Print compact JSON")
    parent.add_argument("--insecure", action="store_true", default=argparse.SUPPRESS, help="Disable SSL certificate verification")
    return parent


def _build_parser() -> argparse.ArgumentParser:
    global_args = _global_parent()
    p = argparse.ArgumentParser(description="Home Assistant API helper", parents=[global_args])

    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("states", parents=[global_args], help="Read /api/states with optional filters")
    ps.add_argument("--domain", help="Filter by entity domain, e.g. sensor")
    ps.add_argument("--contains", help="Filter entity_id substring")
    ps.add_argument("--limit", type=int, help="Limit output rows")

    pe = sub.add_parser("state", parents=[global_args], help="Read one entity from /api/states/<entity_id>")
    pe.add_argument("entity_id", help="Entity ID, e.g. climate.pool")

    ph = sub.add_parser("history", parents=[global_args], help="Read entity history from /api/history/period")
    ph.add_argument("entity_id", help="Entity ID")
    ph.add_argument("--hours", type=float, default=24.0, help="Lookback window in hours (default: 24)")
    ph.add_argument("--minimal", action="store_true", help="Use minimal_response=1")
    ph.add_argument("--no-attributes", action="store_true", help="Use no_attributes=1")
    ph.add_argument("--significant-only", action="store_true", help="Use significant_changes_only=1")

    sub.add_parser("services", parents=[global_args], help="Read /api/services")

    pg = sub.add_parser("get", parents=[global_args], help="Read any GET API path")
    pg.add_argument("path", help="API path, e.g. /api/config")
    pg.add_argument(
        "--query",
        action="append",
        help="Query string item key=value. Can be repeated.",
    )

    pc = sub.add_parser("call", parents=[global_args], help="Call a Home Assistant service (POST /api/services/<domain>/<service>)")
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
        parents=[global_args],
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

    pp = sub.add_parser("pool", parents=[global_args], help="Read a focused pool summary from live states plus remote config options")
    _add_pool_selector_args(pp)
    pp.add_argument("--full", action="store_true", help="Include full attributes for matching entities")

    ppc = sub.add_parser("pool-config", parents=[global_args], help="Read pool_controller config-entry data/options from Home Assistant WebSocket API")
    _add_pool_selector_args(ppc)

    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        ha_url, token, _used, config_insecure = _resolve_credentials(
            getattr(args, "config", None),
            getattr(args, "url", None),
            bool(getattr(args, "local", False)),
        )
        args.timeout = getattr(args, "timeout", 20)
        args.compact = bool(getattr(args, "compact", False))
        args.insecure = bool(getattr(args, "insecure", False) or config_insecure)

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
        elif args.command == "pool":
            _cmd_pool(args, ha_url, token)
        elif args.command == "pool-config":
            _cmd_pool_config(args, ha_url, token)
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
