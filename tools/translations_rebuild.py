#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


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


def _leaf_value_map(data: Dict[str, Any]) -> Dict[str, str]:
    return {
        path: value
        for path, value in _iter_leaf_paths(data)
        if path and isinstance(value, str)
    }


def _rebuild_from_base(base: Any, values: Dict[str, str], prefix: str, placeholder: str) -> Any:
    if isinstance(base, dict):
        return {
            key: _rebuild_from_base(value, values, f"{prefix}.{key}" if prefix else key, placeholder)
            for key, value in base.items()
        }
    if isinstance(base, list):
        return [
            _rebuild_from_base(value, values, f"{prefix}[{idx}]", placeholder)
            for idx, value in enumerate(base)
        ]
    if isinstance(base, str):
        if prefix in values and isinstance(values[prefix], str):
            return values[prefix]
        return f"{placeholder} {prefix}"
    return base


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild translation files from strings.json while preserving existing translations."
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
        "--placeholder",
        default="__TODO_TRANSLATE__",
        help="Placeholder prefix for missing translations (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; only report what would change.",
    )

    args = parser.parse_args()
    base_path = Path(args.base)
    translations_dir = Path(args.translations_dir)

    base = _load_json(base_path)

    for path in sorted(translations_dir.glob("*.json")):
        if path.name == base_path.name:
            continue
        if path.name == "en.json":
            rebuilt = base
        else:
            existing = _load_json(path)
            value_map = _leaf_value_map(existing)
            rebuilt = _rebuild_from_base(base, value_map, "", args.placeholder)

        if args.dry_run:
            print(f"Would rebuild {path}")
        else:
            _write_json(path, rebuilt)
            print(f"Rebuilt {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
