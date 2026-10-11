"""Pure Python computation for connected-app save publishing.

Input: one already-read GitHub campaign and a player action.
Output: one complete proposed compact JSON save plus optimistic-concurrency SHA.
No network, no GitHub token, no file writes, no Codespaces and no extra RNG rolls.
An authenticated GitHub connected app must perform the actual conditional write
and readback. Until then the turn is explicitly UNPERSISTED and not canonical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from .consent import covenant_digest
from .engine import Engine
from .github_saves import BRANCH, REPOSITORY, GitHubSaveError, decode_state, encode_state, remote_path
from .memory import find_event_by_idempotency_key, validate_memory_for_mod
from .mod_loader import load_mod

MODS = {
    "mirror_delivery": "mirror_delivery.json",
    "orbital_swarm_trail": "orbital_swarm_trail.json",
    "great_labyrinth_of_egypt": "great_labyrinth_of_egypt.json",
}
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_KEY = re.compile(r"[a-zA-Z0-9_.:-]{1,128}\Z")
MAX_ACTION_CHARS = 2000
MAX_REQUEST_BYTES = 1_250_000


class TurnExchangeError(ValueError):
    """Input is inconsistent, unsafe, stale or not a resumable public campaign."""


def git_blob_sha(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def safe_mod_path(mod_id: str) -> Path:
    filename = MODS.get(mod_id)
    if not filename:
        raise TurnExchangeError("unknown supported mod ID")
    return Path(__file__).resolve().parents[1] / "mods" / filename


def propose_turn(request: dict) -> dict:
    """Perform exactly one in-memory engine step, but NEVER claim remote persistence."""
    if not isinstance(request, dict):
        raise TurnExchangeError("request must be an object")
    campaign = request.get("campaign_id")
    if not isinstance(campaign, str):
        raise TurnExchangeError("missing campaign ID")
    path = remote_path(campaign)
    mod_id = request.get("mod_id")
    if not isinstance(mod_id, str):
        raise TurnExchangeError("missing mod ID")
    action = request.get("action")
    if not isinstance(action, str) or not action.strip() or len(action) > MAX_ACTION_CHARS:
        raise TurnExchangeError("invalid player action")
    key = request.get("idempotency_key")
    if not isinstance(key, str) or not _KEY.fullmatch(key):
        raise TurnExchangeError("missing or invalid idempotency key")
    expected_sha = request.get("expected_blob_sha")
    if not isinstance(expected_sha, str) or not _SHA.fullmatch(expected_sha):
        raise TurnExchangeError("a verified GitHub blob SHA is required")
    previous_version = request.get("expected_state_version")
    if type(previous_version) is not int or previous_version < 0:
        raise TurnExchangeError("a nonnegative expected state version is required")
    raw = request.get("save_json")
    if not isinstance(raw, str):
        raise TurnExchangeError("save_json must be the exact GitHub file contents")
    raw_bytes = raw.encode("utf-8")
    if git_blob_sha(raw_bytes) != expected_sha:
        raise TurnExchangeError("remote save content disagrees with its declared Git blob SHA")
    state = decode_state(raw_bytes)  # size bound + ledger integrity
    if state.get("state_version") != previous_version:
        raise TurnExchangeError("stale or inconsistent state_version")
    if state.get("turn") != previous_version:
        raise TurnExchangeError("turn and state_version disagree")
    if state.get("mod", {}).get("id") != mod_id:
        raise TurnExchangeError("save/mod mismatch")
    published = state.get("github_publication", {})
    if not isinstance(published, dict) or any((
        published.get("repository") != REPOSITORY,
        published.get("branch") != BRANCH,
        published.get("path") != path,
        published.get("public") is not True,
        published.get("agreement_sha256") != covenant_digest(),
    )):
        raise TurnExchangeError("public destination or current covenant mismatch")
    mod = load_mod(safe_mod_path(mod_id))
    validate_memory_for_mod(state, mod)

    duplicate = find_event_by_idempotency_key(state, key)
    if duplicate is not None:
        if duplicate.get("payload", {}).get("action") != action:
            raise TurnExchangeError("idempotency key was previously used with a different action")
        return {
            "status": "duplicate", "persisted": False, "requires_write": False,
            "remote_verified": False, "authoritative_if_source_verified": True,
            "turn": state["turn"], "state_version": state["state_version"],
            "scene_packet": duplicate.get("payload", {}).get("scene_packet"),
            "expected_blob_sha": expected_sha,
            "repository": REPOSITORY, "branch": BRANCH, "path": path,
        }

    packet = Engine(mod, state).step(action, idempotency_key=key)
    proposed_bytes = encode_state(state)  # bounds, secret scan, hash-chain verification
    return {
        "status": "proposal", "persisted": False, "requires_write": True,
        "remote_verified": False, "new_turn": state["turn"],
        "state_version": state["state_version"],
        "repository": REPOSITORY, "branch": BRANCH, "path": path,
        "expected_blob_sha": expected_sha,
        "proposed_blob_sha": git_blob_sha(proposed_bytes),
        "proposed_save_json": proposed_bytes.decode("utf-8"),
        "scene_packet_location": "proposed_save_json.event_ledger[-1].payload.scene_packet",
        "idempotency_key": key,
        "instructions": (
            "The trusted connected GitHub tool must update this exact path with "
            "expected_blob_sha, then read back proposed_blob_sha; only after "
            "verified persistence may last_scene_packet be narrated as canonical."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Credential-free, local-file-free one-turn proposal; never commits GitHub saves"
    )
    parser.add_argument("--max-request-bytes", type=int, default=MAX_REQUEST_BYTES)
    args = parser.parse_args(argv)
    try:
        if args.max_request_bytes < 1 or args.max_request_bytes > MAX_REQUEST_BYTES:
            raise TurnExchangeError("invalid size bound")
        raw = sys.stdin.buffer.read(args.max_request_bytes + 1)
        if len(raw) > args.max_request_bytes:
            raise TurnExchangeError("input exceeds size limit")
        request = json.loads(raw)
        result = propose_turn(request)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (TurnExchangeError, GitHubSaveError, ValueError, OSError) as exc:
        print(json.dumps({"status": "proposal_refused", "persisted": False, "reason": str(exc)}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
