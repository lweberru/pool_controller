#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'custom_components' / 'pool_controller' / 'translations'
TEMPLATE = ROOT / 'en.json'
LANGS = ['de','es','fr']

def load(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_by_path(d, path):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur

def merge_template(template, trans):
    # Walk template and for each leaf pick trans value if exists otherwise template
    if isinstance(template, dict):
        out = {}
        for k, v in template.items():
            out[k] = merge_template(v, trans.get(k) if isinstance(trans, dict) else None)
        return out
    else:
        # leaf (string)
        return trans if isinstance(trans, str) else template


def main():
    tpl = load(TEMPLATE)
    for lang in LANGS:
        p = ROOT / f"{lang}.json"
        if not p.exists():
            print(f"{lang}.json not found, skipping")
            continue
        trans = load(p)
        merged = merge_template(tpl, trans)
        # Backup
        (p.with_suffix('.json.bak')).write_bytes(p.read_bytes())
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=4)
        lines = sum(1 for _ in open(p, 'r', encoding='utf-8'))
        print(f"Wrote {p} ({lines} lines)")

if __name__ == '__main__':
    main()
