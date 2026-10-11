"""Public GitHub campaign backend for explicit, consented, authoritative turns.

No Codespace, hosted service, or campaign is created merely by importing this
module or running 'preview'. The Player Covenant remains a review draft.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .consent import (
    AGREEMENT_VERSION, SAVE_DISCLOSURE, ConsentError, covenant_digest,
    default_receipt_path, load_receipt,
)
from .engine import Engine
from .memory import (
    find_event_by_idempotency_key, new_memory, validate_memory_for_mod,
    verify_ledger,
)
from .mod_loader import load_mod

REPOSITORY = "Aggredicus/Phenomenal-Engine"
BRANCH = "campaign-saves"
SAVE_PREFIX = "campaigns"
MAX_SAVE_BYTES = 900_000
_CAMPAIGN = re.compile(r"[a-z][a-z0-9_-]{0,47}\Z")
_SECRET = re.compile(
    r"(?:github_pat_[A-Za-z0-9_]{15,}|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


class GitHubSaveError(RuntimeError):
    """A public save was refused or could not be verified."""


def remote_path(campaign: str) -> str:
    if not _CAMPAIGN.fullmatch(campaign):
        raise GitHubSaveError("campaign ID must start with a letter and contain only 1-48 lowercase letters, digits, '-' or '_'")
    return f"{SAVE_PREFIX}/{campaign}.json"


def local_path(campaign: str) -> Path:
    remote_path(campaign)
    return Path("runtime") / (campaign + ".json")


def encode_state(memory: dict) -> bytes:
    if not verify_ledger(memory):
        raise GitHubSaveError("event ledger failed verification")
    payload = (json.dumps(memory, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_SAVE_BYTES:
        raise GitHubSaveError("public save exceeds the configured 900 KB limit")
    if _SECRET.search(payload.decode("utf-8")):
        raise GitHubSaveError("potential credential or private key detected; refused public publication")
    return payload


def decode_state(raw: bytes) -> dict:
    if len(raw) > MAX_SAVE_BYTES:
        raise GitHubSaveError("remote campaign exceeds the configured limit")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise GitHubSaveError("remote campaign is not valid JSON") from exc
    if not isinstance(value, dict) or not verify_ledger(value):
        raise GitHubSaveError("remote campaign ledger is missing or invalid")
    return value


class GitHubAPI:
    """Minimal REST transport; accepts tokens from the environment only."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")

    def request(self, method: str, path: str, data: dict | None = None, *, missing_ok: bool = False):
        if path != "/user" and not path.startswith(f"/repos/{REPOSITORY}/"):
            if path != f"/repos/{REPOSITORY}":
                raise GitHubSaveError("unexpected GitHub API destination")
        if method not in ("GET", "PUT"):
            raise GitHubSaveError("unsupported GitHub API operation")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "PhenomenalEngine-PublicSave/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        body = None if data is None else json.dumps(data).encode("utf-8")
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request("https://api.github.com" + path, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=20) as res:
                return json.loads(res.read(5_000_000).decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            if exc.code in (409, 412, 422):
                raise GitHubSaveError(f"GitHub rejected the write or detected a version conflict (HTTP {exc.code}); reload before retrying") from exc
            raise GitHubSaveError(f"GitHub API returned HTTP {exc.code}; no save was confirmed") from exc
        except (URLError, TimeoutError, ValueError) as exc:
            raise GitHubSaveError("GitHub request failed; no save was confirmed") from exc


def preflight(api: GitHubAPI, receipt: dict) -> None:
    if not api.token:
        raise GitHubSaveError("GITHUB_TOKEN is required; never paste credentials into game chat")
    repo = api.request("GET", f"/repos/{REPOSITORY}")
    if repo.get("full_name", "").lower() != REPOSITORY.lower() or repo.get("private") is not False:
        raise GitHubSaveError("target repository identity or PUBLIC visibility could not be verified")
    if repo.get("permissions", {}).get("push") is False:
        raise GitHubSaveError("authenticated account does not have push permission")
    branch = api.request("GET", f"/repos/{REPOSITORY}/branches/{BRANCH}", missing_ok=True)
    if not branch:
        raise GitHubSaveError("the dedicated public campaign-saves branch does not exist")
    actor = api.request("GET", "/user")
    if str(actor.get("login", "")).lower() != str(receipt["account_id"]).lower():
        raise GitHubSaveError("authenticated GitHub login does not match the covenant receipt")


def fetch_campaign(api: GitHubAPI, campaign: str) -> tuple[dict | None, str | None]:
    path = remote_path(campaign)
    result = api.request(
        "GET", f"/repos/{REPOSITORY}/contents/{path}?ref={quote(BRANCH)}",
        missing_ok=True,
    )
    if result is None:
        return None, None
    if not isinstance(result, dict) or result.get("type") != "file":
        raise GitHubSaveError("campaign path is not a regular file")
    try:
        encoded = result["content"].replace("\n", "")
        blob = base64.b64decode(encoded, validate=True)
        state = decode_state(blob)
        sha = result["sha"]
        if not isinstance(sha, str) or not sha:
            raise ValueError("missing blob SHA")
    except (KeyError, ValueError, TypeError) as exc:
        raise GitHubSaveError("remote save encoding or SHA is invalid") from exc
    return state, sha


def save_campaign(api: GitHubAPI, campaign: str, state: dict, prior_sha: str | None) -> str:
    path = remote_path(campaign)
    raw = encode_state(state)
    data = {
        "message": f"save({campaign}): authoritative turn {state['turn']}",
        "content": base64.b64encode(raw).decode("ascii"),
        "branch": BRANCH,
    }
    if prior_sha:
        data["sha"] = prior_sha  # Optimistic concurrency: reject competing writers.
    result = api.request("PUT", f"/repos/{REPOSITORY}/contents/{path}", data)
    commit_sha = result.get("commit", {}).get("sha")
    if not isinstance(commit_sha, str) or not commit_sha:
        raise GitHubSaveError("GitHub did not confirm a commit")
    checked, checked_sha = fetch_campaign(api, campaign)
    if checked is None or checked_sha != result.get("content", {}).get("sha"):
        raise GitHubSaveError("write returned but a matching remote save could not be verified")
    if encode_state(checked) != raw:
        raise GitHubSaveError("remote save content differs from the intended state")
    return commit_sha


def public_preview(campaign: str, mod_path: str) -> dict:
    path = remote_path(campaign)
    mod = load_mod(mod_path)
    fields = sorted(new_memory(mod, "preview-not-persisted").keys())
    return {
        "status": "preview_only", "published": False,
        "repository": REPOSITORY, "visibility": "PUBLIC", "branch": BRANCH,
        "path": path, "url": f"https://github.com/{REPOSITORY}/blob/{BRANCH}/{path}",
        "mod": {"id": mod["id"], "title": mod["title"], "version": mod["version"]},
        "public_json_top_level_fields": fields,
        "save_disclosure": SAVE_DISCLOSURE,
        "additional_public_metadata": [
            "publication destination and current covenant version/digest",
        ],
        "private_not_uploaded": [
            "local covenant receipt", "GITHUB_TOKEN", "full ChatGPT transcript",
        ],
        "covenant": {"version": AGREEMENT_VERSION, "sha256": covenant_digest()},
        "requirements": [
            "Read python -m phenomenal_engine covenant --full",
            "Create an explicit PUBLIC receipt using accept-covenant, with all four acknowledgements",
            "Use a token with Contents read/write that matches the receipt's authenticated account",
            "Explicitly confirm the first public publication",
        ],
        "warning": "Git history and third-party copies may survive deletion; hidden plot details will be public.",
        "codespaces": "disabled; not used by this command",
    }


def run_turn(
    api: GitHubAPI, *, campaign: str, mod_path: str, action: str,
    idempotency_key: str, seed: str = "story-seed",
    consent_path: str | None = None, confirm_first_publication: bool = False,
) -> dict:
    """One fully remote-persisted turn. Never returns a new scene before verified commit."""
    path = remote_path(campaign)
    if not action.strip() or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise GitHubSaveError("nonempty action and unique idempotency key (max 128 chars) are required")
    if _SECRET.search(action):
        raise GitHubSaveError("possible credential found in player action")
    receipt_file = Path(consent_path) if consent_path else default_receipt_path(local_path(campaign))
    receipt = load_receipt(
        receipt_file, save_path=local_path(campaign),
        repository=REPOSITORY, visibility="public",
    )
    preflight(api, receipt)
    mod = load_mod(mod_path)
    memory, sha = fetch_campaign(api, campaign)
    created = memory is None
    if created:
        if not confirm_first_publication:
            raise GitHubSaveError("new public campaign requires --confirm-first-publication")
        memory = new_memory(mod, seed)
    else:
        validate_memory_for_mod(memory, mod)
        origin = memory.get("github_publication", {})
        if origin.get("repository") != REPOSITORY or origin.get("path") != path or origin.get("branch") != BRANCH:
            raise GitHubSaveError("existing save lacks matching public destination metadata")
    duplicate = find_event_by_idempotency_key(memory, idempotency_key)
    if duplicate is not None:
        return {
            "status": "duplicate", "persisted": True, "created": False,
            "campaign_id": memory["session_id"], "turn": memory["turn"],
            "state_version": memory["state_version"],
            "scene_packet": duplicate.get("payload", {}).get("scene_packet"),
            "repository": REPOSITORY, "branch": BRANCH, "path": path,
            "commit_sha": None, "remote_verified": True,
        }
    if created:
        memory["github_publication"] = {
            "repository": REPOSITORY, "branch": BRANCH, "path": path,
            "public": True, "agreement_version": AGREEMENT_VERSION,
            "agreement_sha256": covenant_digest(),
        }
    packet = Engine(mod, memory).step(action, idempotency_key=idempotency_key)
    commit = save_campaign(api, campaign, memory, sha)
    return {
        "status": "ok", "persisted": True, "created": created,
        "campaign_id": memory["session_id"], "state_version": memory["state_version"],
        "turn": memory["turn"], "scene_packet": packet,
        "repository": REPOSITORY, "branch": BRANCH, "path": path,
        "commit_sha": commit, "remote_verified": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Explicit, public GitHub-backed Phenomenal Engine saves; Codespaces unused"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("preview", "play", "status"):
        p = sub.add_parser(name)
        p.add_argument("campaign", help="1-48-character lowercase save identifier")
        if name != "status":
            p.add_argument("mod", help="path to declarative JSON game mod")
        if name == "play":
            p.add_argument("action", help="player action resolved as exactly one turn")
            p.add_argument("--idempotency-key", required=True)
            p.add_argument("--seed", default="story-seed")
            p.add_argument("--consent-receipt", default=None)
            p.add_argument("--confirm-first-publication", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "preview":
            result = public_preview(args.campaign, args.mod)
        elif args.command == "status":
            api = GitHubAPI()
            state, sha = fetch_campaign(api, args.campaign)
            if state is None:
                raise GitHubSaveError("campaign does not exist")
            result = {
                "status": "ok", "persisted": True, "remote_verified": True,
                "campaign_id": state["session_id"], "mod": state["mod"],
                "turn": state["turn"], "state_version": state["state_version"],
                "repository": REPOSITORY, "branch": BRANCH,
                "path": remote_path(args.campaign), "blob_sha": sha,
            }
        else:
            result = run_turn(
                GitHubAPI(), campaign=args.campaign, mod_path=args.mod,
                action=args.action, idempotency_key=args.idempotency_key,
                seed=args.seed, consent_path=args.consent_receipt,
                confirm_first_publication=args.confirm_first_publication,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (GitHubSaveError, ConsentError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "publication_blocked", "persisted": False,
            "reason": str(exc),
        }, ensure_ascii=False), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
