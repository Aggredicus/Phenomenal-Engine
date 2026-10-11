#!/usr/bin/env python3
"""Local-only Mirror Delivery playtest. No GitHub publishing or new compute."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mods" / "mirror_delivery.json"
LOCAL = ROOT / "runtime"


def engine(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "phenomenal_engine", *args],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    try:
        data = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError("Engine returned no JSON: " + result.stderr.strip()) from exc
    if result.returncode:
        raise RuntimeError("Engine refused the operation: " + json.dumps(data))
    return data


def yes(prompt: str) -> bool:
    return input(prompt + " [type YES]: ").strip() == "YES"


def safe_save(name: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name):
        raise ValueError("Invalid save identifier (letters, digits, - and _ only)")
    return LOCAL / (name + ".json")


def accept(save: Path) -> bool:
    terms = engine("covenant")
    print("\nPHENOMENAL ENGINE — LOCAL PLAYTEST")
    print("This test does NOT publish to GitHub. Files remain under runtime/ (Git-ignored).")
    print("Deleting your Codespace can destroy this local state.")
    print("The Player Covenant is a review draft, NOT an operative hosted-service agreement.")
    print("Your saved player actions, scene packets, hidden world state and RNG are in the local JSON.")
    print("No new billable computing resources are created by this program.")
    print("Terms: " + terms["version"] + " SHA256 " + terms["sha256"])
    print("Review them first: python -m phenomenal_engine covenant --full")
    print("Planned save: " + str(save.relative_to(ROOT)))
    repo = input("Your intended future GitHub save destination (owner/repo): ").strip()
    visibility = input("Your intended future storage choice (type PUBLIC or PRIVATE): ").strip().lower()
    if visibility not in ("public", "private"):
        return False
    if not yes("I understand permanent copying risks of public saves and will avoid private data"):
        return False
    if not yes("I acknowledge conduct rules and that third-party compute needs separate approval"):
        return False
    if not yes("I affirm that I am at least 18 years old"):
        return False
    if not yes("I have reviewed the draft covenant and affirm this technical-playtest acknowledgement"):
        return False
    account = input("Your self-declared GitHub account reference (NOT verified by this test): ").strip()
    result = engine(
        "accept-covenant", str(save), "--account-id", account,
        "--repository", repo, "--visibility", visibility,
        "--storage-choice", visibility, "--publication-understood",
        "--rules-accepted", "--agree", "--adult",
    )
    print("Recorded LOCAL and UNVERIFIED acceptance. Nothing was published.")
    return result["status"] == "accepted_locally_unverified"


def show(result: dict, save: Path) -> None:
    if result.get("persisted") is not True or result.get("status") not in ("ok", "duplicate"):
        raise RuntimeError("Engine did not confirm persistence, so gameplay must not advance")
    print("\n" + "=" * 66)
    print("AUTHORITATIVE LOCAL TURN " + str(result["turn"]))
    print("=" * 66)
    print(json.dumps(result["scene_packet"], ensure_ascii=False, indent=2))
    print("\nLocal save: " + str(save.relative_to(ROOT)))
    print("Verified local persistence: true. Remote GitHub persistence: NOT enabled.")
    print("Paste the scene_packet above into ChatGPT for narration. Do not paste a private save.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Play Mirror Delivery with real local Python")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--new", action="store_true", help="fresh game (default)")
    group.add_argument("--resume", metavar="SAVE_ID", help="resume a local game")
    parser.add_argument("--once", action="store_true", help="play one turn only")
    parser.add_argument("--action", default=None, help="opening action text")
    args = parser.parse_args()
    LOCAL.mkdir(exist_ok=True)
    if args.resume:
        save = safe_save(args.resume)
        if not save.exists():
            print("Save not found: " + str(save), file=sys.stderr)
            return 2
    else:
        name = "mirror-test-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        save = safe_save(name)
        print("Fresh campaign; existing saves will not be overwritten.")
        if not accept(save):
            print("Declined or invalid consent. No game turn was executed.")
            return 3

    action = args.action or "I arrive aboard Morrowglass and request the predeparture mission briefing."
    while True:
        result = engine("play", str(MOD), str(save), action,
                        "--idempotency-key", "playtest-" + uuid.uuid4().hex)
        show(result, save)
        if args.once:
            return 0
        try:
            action = input("\nCaptain Zan's next action (or QUIT): ").strip()
        except EOFError:
            return 0
        if not action or action.upper() == "QUIT":
            return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyboardInterrupt) as exc:
        print("Playtest stopped: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
