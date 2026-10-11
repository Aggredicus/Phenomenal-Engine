"""Read-only turn prelude and verified reveal envelopes.

This is a presentation protocol, not an engine substitute or a scheduler.
It never generates outcomes, changes RNG, writes saves or starts compute.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .memory import load_memory, validate_memory_for_mod
from .mod_loader import load_mod

ALLOWED_PHASES = (
    "state_loaded", "simulation_started", "simulation_completed",
    "save_commit_started", "save_commit_completed", "readback_verified",
)


def _safe_text(value: object, limit: int = 350) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _known_location(mod: dict, memory: dict) -> dict:
    location = memory.get("world_state", {}).get("location")
    if not isinstance(location, str):
        return {}
    for node in mod.get("locations", []):
        if isinstance(node, dict) and node.get("id") == location:
            return node
    return {}


def build_prelude_packet(mod: dict, memory: dict, requested_action: str) -> dict:
    """Ground scene-setting in previously committed state; never pretend action succeeded."""
    validate_memory_for_mod(memory, mod)
    from .memory import verify_ledger
    if not verify_ledger(memory):
        raise ValueError("previous save ledger failed verification")
    action = _safe_text(requested_action, 900)
    if not action:
        raise ValueError("player action is empty")
    last = memory.get("last_scene_packet")
    if last is not None and (not isinstance(last, dict) or last.get("turn") != memory.get("turn")):
        raise ValueError("last scene packet and turn disagree")
    node = _known_location(mod, memory)
    place = _safe_text(node.get("name")) or "your current location"
    location_visual = _safe_text(node.get("visual"), 500)
    player = memory.get("player_identity", {})
    captain = _safe_text(player.get("alias") or player.get("name")) or "Captain"
    sensory = last.get("phenomenology", {}) if isinstance(last, dict) else {}
    auditory = _safe_text(sensory.get("auditory"), 120)
    lines = [
        f"{captain} remains at {place}, as established by the last saved turn.",
    ]
    if location_visual:
        lines.append(location_visual[0].upper() + location_visual[1:] + ".")
    elif auditory:
        lines.append(f"The recorded soundscape remains {auditory}.")
    lines.append(f"Your intended action is: {action}")
    lines.append("The outcome has not yet been resolved; no new time, event, resource or consequence is asserted.")
    return {
        "type": "phenomenal_engine.turn_prelude",
        "version": 1,
        "observer_safe": True,
        "authoritative": False,
        "persisted": False,
        "is_turn_result": False,
        "prior_turn": memory["turn"],
        "requested_action": action,
        "scene_lines": lines,
        "no_rng_consumed": True,
        "no_save_mutated": True,
    }


def prelude_from_files(mod_path: str | Path, save_path: str | Path, action: str) -> dict:
    mod = load_mod(mod_path)
    memory = load_memory(save_path)
    return build_prelude_packet(mod, memory, action)


def phase_event(name: str, *, state_version: int, detail: str = "") -> dict:
    """A caller may emit only at a phase it actually reached; never schedule fake transitions."""
    if name not in ALLOWED_PHASES:
        raise ValueError("unknown execution phase")
    if type(state_version) is not int or state_version < 0:
        raise ValueError("invalid state version")
    return {
        "type": "phenomenal_engine.turn_progress",
        "phase": name,
        "prior_state_version": state_version,
        "detail": _safe_text(detail, 180),
        "authoritative_result": False,
    }


def verified_reveal(run_response: dict) -> dict:
    """Only an independently verified remote commit can unlock consequential narration."""
    if not isinstance(run_response, dict):
        raise ValueError("missing execution response")
    if run_response.get("status") not in ("ok", "duplicate"):
        raise ValueError("engine did not return a completed/duplicate turn")
    if run_response.get("persisted") is not True or run_response.get("remote_verified") is not True:
        raise ValueError("remote save is not verified")
    scene = run_response.get("scene_packet")
    if not isinstance(scene, dict) or scene.get("turn") != run_response.get("turn"):
        raise ValueError("scene packet does not match returned turn")
    if not isinstance(run_response.get("repository"), str) or not run_response["repository"]:
        raise ValueError("missing repository provenance")
    if not isinstance(run_response.get("path"), str) or not run_response["path"]:
        raise ValueError("missing save path provenance")
    return {
        "type": "phenomenal_engine.verified_turn_reveal",
        "authoritative": True,
        "persisted": True,
        "remote_verified": True,
        "turn": run_response["turn"],
        "state_version": run_response["state_version"],
        "scene_packet": scene,
        "repository": run_response["repository"],
        "path": run_response["path"],
        "commit_sha": run_response.get("commit_sha"),
    }


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Read-only established-facts prelude; no RNG/turn execution")
    p.add_argument("mod")
    p.add_argument("save")
    p.add_argument("action")
    args = p.parse_args(argv)
    print(json.dumps(prelude_from_files(args.mod, args.save, args.action), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
