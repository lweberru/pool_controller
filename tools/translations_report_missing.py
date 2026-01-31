#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _iter_leaf_paths(data: Any, prefix: str = "") -> Iterable[Tuple[str, Any]]:
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            yield from _iter_leaf_paths(value, path)
        return
    if isinstance(data, list):
        for idx, value in enumerate(data):
            path = f"{prefix}[{idx}]"
            yield from _iter_leaf_paths(value, path)
        return
    yield prefix, data


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _leaf_key_set(data: Dict[str, Any]) -> set[str]:
    return {path for path, value in _iter_leaf_paths(data) if path and isinstance(value, str)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report missing translation keys compared to strings.json."
    )
    parser.add_argument(
        "--base",
        default="custom_components/pool_controller/strings.json",
        help="Path to strings.json (default: %(default)s)",
    )
    parser.add_argument(
        "--translations-dir",
        default="custom_components/pool_controller/translations",
        help="Directory with translation JSON files (default: %(default)s)",
    )
    parser.add_argument(
        "--include-extra",
        action="store_true",
        help="Also report extra keys not present in strings.json.",
    )

    args = parser.parse_args()
    base_path = Path(args.base)
    translations_dir = Path(args.translations_dir)

    base = _load_json(base_path)
    base_keys = _leaf_key_set(base)

    for path in sorted(translations_dir.glob("*.json")):
        if path.name == base_path.name:
            continue
        data = _load_json(path)
        keys = _leaf_key_set(data)
        missing = sorted(base_keys - keys)
        extra = sorted(keys - base_keys)
        print(f"\n{path.name}: missing={len(missing)}" + (f" extra={len(extra)}" if args.include_extra else ""))
        if missing:
            for key in missing:
                print(f"  MISSING: {key}")
        if args.include_extra and extra:
            for key in extra:
                print(f"  EXTRA: {key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
