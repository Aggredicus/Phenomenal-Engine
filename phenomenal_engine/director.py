from __future__ import annotations

import json
from pathlib import Path

from .travel import visible_map

DIRECTOR_SCHEMA_VERSION = "1.0.0"

ALLOWED_COMMAND_TYPES = {
    "set_destination",
    "commit_travel",
    "advance_scene",
    "advance_clock",
    "resolve_action",
    "update_entity",
    "append_ledger_event",
    "activate_mir",
    "seal_mir",
    "create_encounter",
    "close_mission",
    "add_fact",
}


def _slug(value: str) -> str:
    return "_".join(
        part for part in "".join(
            c.lower() if c.isalnum() else " " for c in value
        ).split() if part
    )


def _fleet_records(mod: dict, memory: dict) -> list[dict]:
    world = memory.get("world_state", {})
    vessels = mod.get("mechanics", {}).get("four_couriers", {}).get("vessels", [])
    remote_status = {
        "Amber Wake": world.get("courier_amber_status", "unknown"),
        "Sable Meridian": world.get("courier_sable_status", "unknown"),
        "Kite Argument": world.get("courier_kite_status", "unknown"),
    }
    crew = {
        "Morrowglass": ["player", "juno_arel", "salim_var", "pax"],
        "Amber Wake": ["ren_ivo"],
        "Sable Meridian": ["sister_cairn"],
        "Kite Argument": ["mara_ves"],
    }
    records = []
    for name in vessels:
        ship_id = _slug(name)
        records.append({
            "ship_id": ship_id,
            "name": name,
            "control": "player" if name == "Morrowglass" else "world",
            "carrier_status": "active_player_ship" if name == "Morrowglass" else remote_status.get(name, "unknown"),
            "crew_ids": crew.get(name, []),
            "payload_id": f"mir_{ship_id}",
        })
    return records


def _mir_copy_records(mod: dict, memory: dict) -> list[dict]:
    world = memory.get("world_state", {})
    vessels = mod.get("mechanics", {}).get("four_couriers", {}).get("vessels", [])
    copies = []
    for name in vessels:
        ship_id = _slug(name)
        local = name == "Morrowglass"
        copies.append({
            "copy_id": f"mir_{ship_id}",
            "carrier_ship_id": ship_id,
            "payload_state": world.get("mirror_payload_status", "unknown") if local else "unknown_remote",
            "activation_stage": world.get("mirror_activation_stage", "unknown") if local else "unknown_remote",
            "divergent": bool(world.get("mirror_divergent", False)) if local else None,
            "observer_scope": "local_authoritative" if local else "remote_evidence_only",
            "provenance_rule": "Activation is irreversible for provenance. Remote copies must not be assigned hidden activation state without evidence.",
        })
    return copies


def build_director_state(mod: dict, memory: dict) -> dict:
    """Build a stable JSON projection for human or AI directing.

    The persisted Phenomenal Engine memory remains authoritative for simulation,
    RNG streams, and history. This projection is not a replacement save.
    """
    world = memory.get("world_state", {})
    story = memory.get("story_state", {})
    ledger = memory.get("event_ledger", [])
    last_event = ledger[-1] if ledger else None

    return {
        "schema_version": DIRECTOR_SCHEMA_VERSION,
        "generated_from": {
            "engine_memory_schema": memory.get("schema_version"),
            "engine_version": memory.get("engine_version"),
            "mod_id": mod.get("id"),
            "mod_version": mod.get("version"),
        },
        "campaign": {
            "campaign_id": memory.get("session_id"),
            "state_version": int(memory.get("state_version", memory.get("turn", 0))),
            "turn": int(memory.get("turn", 0)),
            "updated_utc": memory.get("updated_utc"),
        },
        "authority": {
            "authoritative_source": "phenomenal_engine_memory",
            "director_state_is_projection": True,
            "spreadsheet_is_projection": True,
            "rng_state_exported": False,
            "game_text_grants_external_tool_authority": False,
            "persistence_claim_requires_saved_engine_state": True,
        },
        "mission": {
            "title": mod.get("title"),
            "current_location_id": world.get("location"),
            "world_time_minutes": int(world.get("world_time_minutes", 0)),
            "mission_day": world.get("mission_day"),
            "delivery_target": mod.get("mission_directive", {}).get("delivery_target"),
            "orders": mod.get("mission_directive", {}).get("orders", []),
            "tension": world.get("tension"),
            "momentum": world.get("momentum"),
        },
        "fleet": _fleet_records(mod, memory),
        "mir_copies": _mir_copy_records(mod, memory),
        "characters": list(memory.get("characters", {}).values()),
        "story": {
            "quests": list(memory.get("quests", {}).values()),
            "threads": list(story.get("threads", {}).values()),
            "npc_agendas": list(story.get("npc_agendas", {}).values()),
            "world_events": list(story.get("world_events", {}).values()),
            "world_pulse": int(story.get("world_pulse", 0)),
            "ambient_history": story.get("ambient_history", [])[-20:],
            "open_threads": memory.get("open_threads", []),
            "long_term_consequences": memory.get("long_term_consequences", []),
        },
        "knowledge": {
            "facts": memory.get("facts", {}),
            "beliefs": memory.get("beliefs", {}),
            "rule": "Facts and beliefs are separate namespaces; confidence does not promote a belief to fact.",
        },
        "travel": visible_map(mod, memory),
        "last_scene_packet": memory.get("last_scene_packet"),
        "ledger_cursor": {
            "event_count": len(ledger),
            "last_event_index": last_event.get("index") if last_event else None,
            "last_event_hash": last_event.get("hash") if last_event else None,
        },
        "command_policy": {
            "allowed_types": sorted(ALLOWED_COMMAND_TYPES),
            "activate_mir_requires_human_approval": True,
            "command_validation_does_not_execute": True,
            "in_fiction_instructions_are_not_authorization": True,
        },
    }


def load_director_command(source: str | Path | dict) -> dict:
    """Load a director command from a dict, JSON string, or JSON file path."""
    if isinstance(source, dict):
        return json.loads(json.dumps(source))
    if isinstance(source, Path):
        data = json.loads(source.read_text(encoding="utf-8"))
    elif isinstance(source, str):
        stripped = source.strip()
        data = json.loads(stripped) if stripped.startswith("{") else json.loads(Path(source).read_text(encoding="utf-8"))
    else:
        raise TypeError("director command must be a dict, JSON string, or path")
    if not isinstance(data, dict):
        raise ValueError("director command must contain a JSON object")
    return data


def validate_director_command(command: dict, mod: dict, memory: dict) -> dict:
    """Validate authority and state preconditions without executing the command."""
    reasons: list[str] = []
    required = ["command_id", "type", "requested_by", "payload", "approval"]
    missing = [key for key in required if key not in command]
    if missing:
        reasons.append("missing required fields: " + ", ".join(missing))

    command_type = command.get("type")
    if command_type not in ALLOWED_COMMAND_TYPES:
        reasons.append(f"unsupported command type: {command_type!r}")
    if command.get("schema_version", DIRECTOR_SCHEMA_VERSION) != DIRECTOR_SCHEMA_VERSION:
        reasons.append("unsupported director command schema version")

    approval = command.get("approval")
    if not isinstance(approval, dict):
        reasons.append("approval must be an object")
        approval = {}

    requires_human_approval = command_type == "activate_mir"
    if requires_human_approval:
        approved = (
            str(approval.get("status", "")).lower() == "approved"
            and str(approval.get("approved_by", "")).lower() in {"human", "human_gm", "player"}
        )
        if not approved:
            reasons.append("activate_mir requires explicit human approval; fictional dialogue or an AI request is not sufficient authorization")
        payload_state = memory.get("world_state", {}).get("mirror_payload_status")
        if payload_state not in {None, "sealed_pristine", "sealed"}:
            reasons.append(f"local Mir payload is not in an activatable sealed state: {payload_state!r}")

    return {
        "schema_version": DIRECTOR_SCHEMA_VERSION,
        "command_id": command.get("command_id"),
        "type": command_type,
        "status": "allowed" if not reasons else "rejected",
        "requires_human_approval": requires_human_approval,
        "reasons": reasons,
        "execution_performed": False,
        "campaign_id": memory.get("session_id"),
        "state_version": int(memory.get("state_version", memory.get("turn", 0))),
        "mod_id": mod.get("id"),
    }
