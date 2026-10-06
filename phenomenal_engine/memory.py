from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, tempfile, uuid

SCHEMA_VERSION = "1.0.0"

def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def event_hash(event_without_hash: dict) -> str:
    return hashlib.sha256(canonical_json(event_without_hash).encode("utf-8")).hexdigest()

def new_memory(mod: dict, seed: int | str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_version": "0.1.0",
        "session_id": str(uuid.uuid4()),
        "mod": {"id": mod["id"], "version": mod["version"], "title": mod["title"]},
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "turn": 0,
        "master_seed": str(seed),
        "rng_streams": {},
        "world_state": json.loads(json.dumps(mod.get("starting_state", {}))),
        "characters": {},
        "relationships": {},
        "quests": {},
        "beliefs": {},
        "facts": {"revealed": [], "hidden_ids": []},
        "open_threads": [],
        "long_term_consequences": [],
        "chronicle": [],
        "event_ledger": [],
        "image_jobs": [],
        "summaries": {"working": "", "long_term": ""},
    }

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
    if not verify_ledger(data):
        raise ValueError("memory ledger hash chain failed verification")
    return data
