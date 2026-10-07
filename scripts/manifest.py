from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.json"

def canonical_paths() -> list[Path]:
    paths = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if ".git" in parts or "__pycache__" in parts:
            continue
        if p.name.endswith((".pyc", ".pyo")):
            continue
        if rel.as_posix() == "MANIFEST.json":
            continue
        paths.append(p)
    return sorted(paths, key=lambda p: p.relative_to(ROOT).as_posix())

def build_manifest() -> list[dict]:
    entries = []
    for p in canonical_paths():
        data = p.read_bytes()
        entries.append({
            "path": p.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return entries

def manifest_text(entries: list[dict] | None = None) -> str:
    return json.dumps(entries or build_manifest(), indent=2, ensure_ascii=False) + "\n"

def check() -> bool:
    expected = build_manifest()
    try:
        actual = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        actual = None
    if actual == expected:
        print(f"Verified {len(expected)} manifest entries.")
        return True
    print("MANIFEST_MISMATCH")
    print("----- BEGIN EXPECTED MANIFEST -----")
    print(manifest_text(expected), end="")
    print("----- END EXPECTED MANIFEST -----")
    return False

def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate or verify Phenomenal Engine MANIFEST.json")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--print", dest="print_manifest", action="store_true")
    args = ap.parse_args(argv)

    if args.check:
        raise SystemExit(0 if check() else 1)
    if args.write:
        text = manifest_text()
        MANIFEST.write_text(text, encoding="utf-8")
        print(f"Wrote {len(build_manifest())} manifest entries to {MANIFEST}")
        return
    print(manifest_text(), end="")

if __name__ == "__main__":
    main()
