#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class RepoPaths:
    backend_root: Path
    frontend_root: Path
    backend_manifest: Path
    backend_changelog: Path
    frontend_main: Path


def run(cmd: list[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({cwd}): {' '.join(cmd)}\n\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return (proc.stdout or "").strip()


def read_backend_version(manifest_path: Path) -> str:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return str(data["version"])


def write_backend_version(manifest_path: Path, version: str) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["version"] = version
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_frontend_version(main_js_path: Path) -> str:
    text = main_js_path.read_text(encoding="utf-8")
    m = re.search(r'const VERSION = "([0-9]+\.[0-9]+\.[0-9]+)";', text)
    if not m:
        raise RuntimeError("Could not find VERSION constant in frontend main.js")
    return m.group(1)


def write_frontend_version(main_js_path: Path, version: str) -> None:
    text = main_js_path.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r'const VERSION = "[0-9]+\.[0-9]+\.[0-9]+";',
        f'const VERSION = "{version}";',
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not update VERSION constant in frontend main.js")
    main_js_path.write_text(new_text, encoding="utf-8")


def bump_patch(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver: {version}")
    major, minor, patch = [int(p) for p in parts]
    return f"{major}.{minor}.{patch + 1}"


def bump_minor(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver: {version}")
    major, minor, _patch = [int(p) for p in parts]
    return f"{major}.{minor + 1}.0"


def prompt_with_default(label: str, default: str, assume_yes: bool) -> str:
    if assume_yes:
        return default
    value = input(f"{label} [{default}]: ").strip()
    return value or default


def prompt_multiline(title: str, assume_yes: bool) -> list[str]:
    if assume_yes:
        return []
    print(title)
    print("  (Eine Zeile pro Bullet; mit einzelner '.' Zeile beenden)")
    lines: list[str] = []
    while True:
        line = input("  - ").rstrip()
        if line == ".":
            break
        if line:
            lines.append(line)
    return lines


def _resolve_path(path_str: str | None, base_dir: Path) -> Path | None:
    if not path_str:
        return None
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p


def read_notes_file(path: Path | None) -> list[str]:
    if path is None:
        return []
    if not path.exists():
        raise RuntimeError(f"Notes file not found: {path}")
    text = path.read_text(encoding="utf-8")
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s*", "", line)
        if line:
            lines.append(line)
    return lines


def default_version_for_release_type(current: str, release_type: str) -> str:
    if release_type == "minor":
        return bump_patch(current)
    if release_type == "major":
        return bump_minor(current)
    if release_type == "manual":
        return current
    raise ValueError(f"Unsupported release type: {release_type}")


def prepend_changelog_entry(changelog_path: Path, version: str, notes: list[str]) -> None:
    text = changelog_path.read_text(encoding="utf-8")
    marker = "All notable changes to this integration are documented in this file."
    idx = text.find(marker)
    if idx < 0:
        raise RuntimeError("Could not find changelog marker line")

    today = date.today().isoformat()
    body_lines = notes if notes else ["Release update."]
    bullet_block = "\n".join([f"- {line}" for line in body_lines])
    entry = f"\n\n## [{version}] - {today}\n{bullet_block}\n"

    insert_at = idx + len(marker)
    new_text = text[:insert_at] + entry + text[insert_at:]
    changelog_path.write_text(new_text, encoding="utf-8")


def release_exists(repo: str, tag: str, backend_root: Path) -> bool:
    proc = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo],
        cwd=str(backend_root),
        text=True,
        capture_output=True,
    )
    return proc.returncode == 0


def create_release(repo: str, tag: str, title: str, notes: list[str], cwd: Path) -> None:
    release_notes = "\n".join([f"- {line}" for line in notes]) if notes else "- Release update."
    run(["gh", "release", "create", tag, "--repo", repo, "--title", title, "--notes", release_notes], cwd)


def ensure_clean_or_continue(paths: RepoPaths, assume_yes: bool, target: str) -> None:
    include_backend = target in ("backend", "both")
    include_frontend = target in ("frontend", "both")

    b = run(["git", "status", "--short"], paths.backend_root) if include_backend else ""
    f = run(["git", "status", "--short"], paths.frontend_root) if include_frontend else ""
    if not b and not f:
        return
    if assume_yes:
        return
    print("\nAktuelle Änderungen:")
    if b:
        print("backend:\n" + b)
    if f:
        print("frontend:\n" + f)
    answer = input("Fortfahren und Änderungen für Release committen? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        raise RuntimeError("Abgebrochen durch Benutzer")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and publish HACS releases for backend/frontend repos")
    parser.add_argument("--yes", action="store_true", help="Non-interactive defaults")
    parser.add_argument("--apply-only", action="store_true", help="Only update version files/changelog, no git/release actions")
    parser.add_argument("--target", choices=["backend", "frontend", "both"], default="both", help="Select release target")
    parser.add_argument(
        "--release-type",
        choices=["minor", "major", "manual"],
        default="minor",
        help="Version bump strategy: minor=fix (x.y.z -> x.y.z+1), major=feature (x.y.z -> x.(y+1).0), manual=enter explicit version",
    )
    parser.add_argument("--backend-version", help="Override backend version")
    parser.add_argument("--frontend-version", help="Override frontend version")
    parser.add_argument("--backend-commit-message", help="Override backend commit message")
    parser.add_argument("--frontend-commit-message", help="Override frontend commit message")
    parser.add_argument("--backend-release-title", help="Override backend release title")
    parser.add_argument("--frontend-release-title", help="Override frontend release title")
    parser.add_argument("--notes-file", help="Use one notes file for both backend/frontend release notes")
    parser.add_argument("--backend-notes-file", help="Use notes file for backend release notes")
    parser.add_argument("--frontend-notes-file", help="Use notes file for frontend release notes")
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[1]
    frontend_root = backend_root.parent / "pool_controller_dashboard_frontend"
    paths = RepoPaths(
        backend_root=backend_root,
        frontend_root=frontend_root,
        backend_manifest=backend_root / "custom_components/pool_controller/manifest.json",
        backend_changelog=backend_root / "CHANGELOG.md",
        frontend_main=frontend_root / "main.js",
    )

    include_backend = args.target in ("backend", "both")
    include_frontend = args.target in ("frontend", "both")

    if include_frontend and not paths.frontend_main.exists():
        raise RuntimeError(f"Frontend repo not found: {paths.frontend_root}")

    current_backend = read_backend_version(paths.backend_manifest) if include_backend else None
    current_frontend = read_frontend_version(paths.frontend_main) if include_frontend else None

    backend_version = None
    frontend_version = None

    if args.release_type == "manual" and args.yes and (include_backend and not args.backend_version) and (include_frontend and not args.frontend_version):
        raise RuntimeError("--release-type manual with --yes requires --backend-version and/or --frontend-version")

    if include_backend:
        backend_default = default_version_for_release_type(current_backend, args.release_type)
        backend_version = args.backend_version or prompt_with_default(
            "Backend Version", backend_default, args.yes
        )
    if include_frontend:
        frontend_default = default_version_for_release_type(current_frontend, args.release_type)
        frontend_version = args.frontend_version or prompt_with_default(
            "Frontend Version", frontend_default, args.yes
        )

    backend_notes: list[str] = []
    frontend_notes: list[str] = []

    notes_file_all = _resolve_path(args.notes_file, backend_root)
    backend_notes_file = _resolve_path(args.backend_notes_file, backend_root) or notes_file_all
    frontend_notes_file = _resolve_path(args.frontend_notes_file, backend_root) or notes_file_all

    if include_backend:
        backend_notes = read_notes_file(backend_notes_file) if backend_notes_file else prompt_multiline("Backend Release Notes", args.yes)
    if include_frontend:
        frontend_notes = read_notes_file(frontend_notes_file) if frontend_notes_file else prompt_multiline("Frontend Release Notes", args.yes)

    if include_backend:
        write_backend_version(paths.backend_manifest, backend_version)
        prepend_changelog_entry(paths.backend_changelog, backend_version, backend_notes)
    if include_frontend:
        write_frontend_version(paths.frontend_main, frontend_version)

    updated = []
    if include_backend:
        updated.append(f"backend={backend_version}")
    if include_frontend:
        updated.append(f"frontend={frontend_version}")
    print(f"\nUpdated versions: {', '.join(updated)}")

    if args.apply_only:
        print("Apply-only mode complete. No git commits/tags/releases created.")
        return

    ensure_clean_or_continue(paths, args.yes, args.target)

    if include_backend:
        run(["git", "add", "-A"], paths.backend_root)
        backend_commit_message = args.backend_commit_message or f"release: v{backend_version}"
        run(["git", "commit", "-m", backend_commit_message], paths.backend_root)

    if include_frontend:
        run(["git", "add", "-A"], paths.frontend_root)
        frontend_commit_message = args.frontend_commit_message or f"release: v{frontend_version}"
        run(["git", "commit", "-m", frontend_commit_message], paths.frontend_root)

    if include_backend:
        run(["git", "push", "origin", "main"], paths.backend_root)
    if include_frontend:
        run(["git", "push", "origin", "main"], paths.frontend_root)

    backend_tag = f"v{backend_version}" if include_backend else None
    frontend_tag = f"v{frontend_version}" if include_frontend else None
    backend_release_title = args.backend_release_title or backend_tag
    frontend_release_title = args.frontend_release_title or frontend_tag

    if include_backend:
        if not release_exists("lweberru/pool_controller", backend_tag, paths.backend_root):
            create_release("lweberru/pool_controller", backend_tag, backend_release_title, backend_notes, paths.backend_root)
        else:
            print(f"Backend release already exists: {backend_tag}")

    if include_frontend:
        if not release_exists("lweberru/pool_controller_dashboard_frontend", frontend_tag, paths.backend_root):
            create_release("lweberru/pool_controller_dashboard_frontend", frontend_tag, frontend_release_title, frontend_notes, paths.backend_root)
        else:
            print(f"Frontend release already exists: {frontend_tag}")

    print("Release process completed successfully.")


if __name__ == "__main__":
    main()
