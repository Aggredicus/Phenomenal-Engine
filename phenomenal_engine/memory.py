from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, tempfile, uuid

from .story import initial_player_experience, initial_story_state

SCHEMA_VERSION = "1.0.0"
ENGINE_VERSION = "0.2.1"

def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def event_hash(event_without_hash: dict) -> str:
    return hashlib.sha256(canonical_json(event_without_hash).encode("utf-8")).hexdigest()

def _copy_json(value):
    return json.loads(json.dumps(value))

def new_memory(mod: dict, seed: int | str) -> dict:
    characters = {
        item["id"]: _copy_json(item)
        for item in mod.get("characters", [])
        if isinstance(item, dict) and item.get("id")
    }
    quests = {}
    for item in mod.get("quests", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        quest = _copy_json(item)
        quest.setdefault("status", item.get("initial_status", "open"))
        quests[item["id"]] = quest

    memory = {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "session_id": str(uuid.uuid4()),
        "state_version": 0,
        "mod": {"id": mod["id"], "version": mod["version"], "title": mod["title"]},
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "turn": 0,
        "master_seed": str(seed),
        "rng_streams": {},
        "world_state": _copy_json(mod.get("starting_state", {})),
        "characters": characters,
        "relationships": {},
        "quests": quests,
        "beliefs": {},
        "facts": {"revealed": [], "hidden_ids": []},
        "open_threads": [],
        "long_term_consequences": [],
        "chronicle": [],
        "event_ledger": [],
        "image_jobs": [],
        "last_scene_packet": None,
        "summaries": {"working": "", "long_term": ""},
        "story_state": initial_story_state(mod),
        "player_experience": initial_player_experience(),
    }
    append_event(
        memory,
        "campaign_created",
        {"mod_id": mod["id"], "mod_version": mod["version"]},
    )
    return memory

def append_event(memory: dict, kind: str, payload: dict) -> dict:
    prev = memory["event_ledger"][-1]["hash"] if memory["event_ledger"] else "GENESIS"
    body = {
        "index": len(memory["event_ledger"]),
        "turn": memory.get("turn", 0),
        "kind": kind,
        "payload": payload,
        "prev_hash": prev,
    }
    body["hash"] = event_hash(body)
    memory["event_ledger"].append(body)
    memory["updated_utc"] = datetime.now(timezone.utc).isoformat()
    return body

def verify_ledger(memory: dict) -> bool:
    prev = "GENESIS"
    for event in memory.get("event_ledger", []):
        saved = event.get("hash")
        body = {k: v for k, v in event.items() if k != "hash"}
        if body.get("prev_hash") != prev or event_hash(body) != saved:
            return False
        prev = saved
    return True

def validate_memory_for_mod(memory: dict, mod: dict, allow_version_mismatch: bool = False) -> None:
    saved_mod = memory.get("mod", {})
    if saved_mod.get("id") != mod.get("id"):
        raise ValueError(
            f"save belongs to mod {saved_mod.get('id')!r}, not {mod.get('id')!r}"
        )
    if not allow_version_mismatch and saved_mod.get("version") != mod.get("version"):
        raise ValueError(
            "save/mod version mismatch: "
            f"{saved_mod.get('version')!r} != {mod.get('version')!r}; "
            "migrate the save or pass --allow-mod-version-mismatch intentionally"
        )

def find_event_by_idempotency_key(memory: dict, key: str | None) -> dict | None:
    if not key:
        return None
    for event in reversed(memory.get("event_ledger", [])):
        payload = event.get("payload", {})
        if payload.get("idempotency_key") == key:
            return event
    return None

def save_memory(path: str | Path, memory: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(memory, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=p.name, suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def load_memory(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("memory file must contain a JSON object")
    if not verify_ledger(data):
        raise ValueError("memory ledger hash chain failed verification")
    data.setdefault("state_version", int(data.get("turn", 0)))
    data.setdefault("last_scene_packet", None)
    data.setdefault("story_state", {"world_pulse": 0, "threads": {}, "npc_agendas": {}, "world_events": {}, "ambient_history": []})
    data.setdefault("player_experience", initial_player_experience())
    return data
