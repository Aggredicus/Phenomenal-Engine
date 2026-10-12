"""Lossless, bounded transport compression; runtime ledgers remain ordinary JSON."""
from __future__ import annotations
import base64
import binascii
import hashlib
import json
import zlib

MAX_ARCHIVE_BYTES = 64_000_000
CODEC = "zlib-base64-v1"


def archive_ledger(packed):
    ledger = packed.get("event_ledger", [])
    if len(ledger) < 2:
        return packed
    raw = json.dumps(ledger[:-1], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("ledger archive exceeds expanded size limit")
    return {**packed, "event_ledger": ledger[-1:], "event_ledger_archive": {
        "codec": CODEC, "event_count": len(ledger) - 1, "expanded_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data": base64.b64encode(zlib.compress(raw, 9)).decode("ascii")}}


def restore_archived_ledger(value):
    archive = value.get("event_ledger_archive")
    if archive is None:
        return value
    if not isinstance(archive, dict) or set(archive) != {"codec", "event_count", "expanded_bytes", "sha256", "data"} or archive.get("codec") != CODEC:
        raise ValueError("invalid ledger archive metadata")
    count, size = archive["event_count"], archive["expanded_bytes"]
    if type(count) is not int or count < 1 or type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES:
        raise ValueError("invalid ledger archive bounds")
    if not isinstance(archive["data"], str) or not isinstance(value.get("event_ledger"), list):
        raise ValueError("invalid ledger archive encoding")
    try:
        compressed = base64.b64decode(archive["data"], validate=True)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, size + 1)
        if len(raw) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("ledger archive is truncated, trailing or exceeds declared bounds")
        if hashlib.sha256(raw).hexdigest() != archive["sha256"]:
            raise ValueError("ledger archive digest mismatch")
        events = json.loads(raw)
    except (binascii.Error, zlib.error, UnicodeDecodeError, TypeError) as exc:
        raise ValueError("invalid ledger archive data") from exc
    if not isinstance(events, list) or len(events) != count or any(not isinstance(event, dict) for event in events):
        raise ValueError("ledger archive event count mismatch")
    value["event_ledger"] = events + value["event_ledger"]
    del value["event_ledger_archive"]
    return value
