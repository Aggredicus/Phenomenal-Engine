"""Consent receipts for local Phenomenal Engine play.

This checks recorded acknowledgements; it does not authenticate a GitHub identity or
verify repository visibility. The official GitHub bridge must do both independently.
The covenant is a REVIEW DRAFT and is not legal approval for a hosted launch.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

AGREEMENT_VERSION = "DRAFT-0.1"
SCHEMA_VERSION = "1.0"
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REQUIRED = ("publication_understood", "rules_and_compute_accepted", "agreement_accepted", "age_18_or_older")


class ConsentError(ValueError):
    """Consent is missing, expired, incomplete, or inconsistent."""


def covenant_path() -> Path:
    return Path(__file__).resolve().parents[1] / "docs" / "PLAYER_COVENANT.md"


def covenant_text() -> str:
    return covenant_path().read_text(encoding="utf-8")


def covenant_digest() -> str:
    return hashlib.sha256(covenant_text().encode("utf-8")).hexdigest()


def default_receipt_path(save_path: str | Path) -> Path:
    save = Path(save_path)
    return save.with_name(save.name + ".consent.json")


SAVE_DISCLOSURE = {
    "saved": [
        "player identity and actions", "scene packets and event ledger",
        "world and quest state including hidden game facts",
        "saved RNG streams", "campaign metadata and timestamps",
    ],
    "not_saved_automatically": [
        "complete ChatGPT transcript", "provider credentials", "private abuse reports",
    ],
}


def create_receipt(
    *, save_path: str | Path, account_id: str, repository: str,
    visibility: str, storage_choice: str,
    publication_understood: bool = False, rules_and_compute_accepted: bool = False,
    agreement_accepted: bool = False, age_18_or_older: bool = False,
) -> dict:
    if not account_id.strip():
        raise ConsentError("an account identifier is required")
    if not _REPO.fullmatch(repository) or ".." in repository:
        raise ConsentError("repository must be owner/repository")
    if visibility not in ("public", "private") or storage_choice != visibility:
        raise ConsentError("storage choice must match repository visibility")
    acknowledgements = {
        "publication_understood": publication_understood,
        "rules_and_compute_accepted": rules_and_compute_accepted,
        "agreement_accepted": agreement_accepted,
        "age_18_or_older": age_18_or_older,
    }
    if any(v is not True for v in acknowledgements.values()):
        raise ConsentError("all four explicit acknowledgements are required")
    return {
        "schema_version": SCHEMA_VERSION,
        "agreement_version": AGREEMENT_VERSION,
        "agreement_sha256": covenant_digest(),
        "accepted_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "github",
        "account_id": account_id,
        "repository": repository,
        "visibility": visibility,
        "storage_choice": storage_choice,
        "save_filename": Path(save_path).name,
        "verification_method": "player_declared_unverified",
        "acknowledgements": acknowledgements,
    }


def verify_receipt(receipt: dict, *, save_path: str | Path, repository: str | None = None,
                   visibility: str | None = None) -> dict:
    if not isinstance(receipt, dict):
        raise ConsentError("receipt must be a JSON object")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise ConsentError("unsupported consent schema")
    if receipt.get("agreement_version") != AGREEMENT_VERSION or receipt.get("agreement_sha256") != covenant_digest():
        raise ConsentError("covenant changed; acceptance must be renewed")
    if receipt.get("provider") != "github" or not str(receipt.get("account_id", "")).strip():
        raise ConsentError("missing account reference")
    if receipt.get("verification_method") != "player_declared_unverified":
        raise ConsentError("unexpected verification method")
    if not _REPO.fullmatch(str(receipt.get("repository", ""))):
        raise ConsentError("invalid repository")
    if receipt.get("save_filename") != Path(save_path).name:
        raise ConsentError("receipt belongs to a different save filename")
    selected = receipt.get("visibility")
    if selected not in ("public", "private") or receipt.get("storage_choice") != selected:
        raise ConsentError("repository visibility and storage choice disagree")
    if repository is not None and repository != receipt.get("repository"):
        raise ConsentError("repository mismatch")
    if visibility is not None and visibility != selected:
        raise ConsentError("visibility mismatch")
    if any(receipt.get("acknowledgements", {}).get(k) is not True for k in _REQUIRED):
        raise ConsentError("one or more acknowledgements are missing")
    try:
        timestamp = datetime.fromisoformat(receipt["accepted_at_utc"])
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("naive UTC timestamp")
    except (ValueError, TypeError, KeyError) as e:
        raise ConsentError("invalid accepted_at_utc timestamp") from e
    return receipt


def load_receipt(path: str | Path, *, save_path: str | Path, repository: str | None = None,
                 visibility: str | None = None) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ConsentError("consent receipt is missing or unreadable") from e
    return verify_receipt(value, save_path=save_path, repository=repository, visibility=visibility)


def write_receipt(path: str | Path, value: dict) -> None:
    # A receipt is written only after explicit affirmative CLI flags. Do not
    # overwrite a previously accepted receipt without an explicit new request.
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")
