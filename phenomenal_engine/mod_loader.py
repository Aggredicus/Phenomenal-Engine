from __future__ import annotations
from pathlib import Path
import json

REQUIRED = {
    "schema_version": str,
    "id": str,
    "title": str,
    "version": str,
    "premise": str,
    "simulation_profile": dict,
    "starting_state": dict,
    "world_model": dict,
    "quests": list,
    "mechanics": dict,
    "llm_directives": list,
}

OPTIONAL_TYPES = {
    "story_design": dict,
    "mission_directive": dict,
    "hidden_truths": dict,
    "main_arc": list,
    "story_threads": list,
    "npc_agendas": list,
    "world_events": list,
    "action_rules": list,
    "conflict_model": dict,
    "travel_network": dict,
    "factions": list,
    "characters": list,
    "locations": list,
    "clocks": list,
    "encounters": list,
}

def validate_mod(mod: dict) -> list[str]:
    errors = []
    for key, typ in REQUIRED.items():
        if key not in mod:
            errors.append(f"missing required key: {key}")
        elif not isinstance(mod[key], typ):
            errors.append(f"{key} must be {typ.__name__}")
    for key, typ in OPTIONAL_TYPES.items():
        if key in mod and not isinstance(mod[key], typ):
            errors.append(f"{key} must be {typ.__name__}")
    if "id" in mod and (not mod["id"] or any(c.isspace() for c in mod["id"])):
        errors.append("id must be nonempty and contain no whitespace")
    if "simulation_profile" in mod:
        cadence = mod["simulation_profile"].get("image_cadence", "key_moments")
        if cadence not in {"off", "every_turn", "key_moments"} and not str(cadence).startswith("every_"):
            errors.append("unsupported image_cadence")
    for thread in mod.get("story_threads", []):
        if not isinstance(thread, dict):
            errors.append("story_threads entries must be objects")
            continue
        if not thread.get("id"):
            errors.append("story_threads entries require id")
        tier = thread.get("tier", "side")
        if tier not in {"main", "faction", "side", "local", "emergent"}:
            errors.append(f"unsupported story thread tier: {tier}")
    return errors

def load_mod(path: str | Path) -> dict:
    mod = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_mod(mod)
    if errors:
        raise ValueError("invalid mod:\n- " + "\n- ".join(errors))
    return mod
