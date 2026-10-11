"""Offline tests: no real GitHub writes, tokens, Codespaces, or bills."""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from phenomenal_engine.consent import create_receipt, write_receipt
from phenomenal_engine.github_saves import (
    BRANCH, REPOSITORY, GitHubSaveError, decode_state, encode_state,
    public_preview, remote_path, run_turn,
)
from phenomenal_engine.memory import verify_ledger

ROOT = Path(__file__).resolve().parents[1]
MOD = str(ROOT / "mods" / "mirror_delivery.json")


class FakeGitHub:
    def __init__(self):
        self.token = "fixture-not-real"
        self.actor = "Aggredicus"
        self.private = False
        self.branch_exists = True
        self.bytes = None
        self.blob_sha = None
        self.commits = 0
        self.reject_put = False
        self.requests = []

    def request(self, method, path, data=None, *, missing_ok=False):
        self.requests.append((method, path))
        if method == "GET" and path == f"/repos/{REPOSITORY}":
            return {
                "full_name": REPOSITORY, "private": self.private,
                "permissions": {"push": True},
            }
        if method == "GET" and path == f"/repos/{REPOSITORY}/branches/{BRANCH}":
            return {"name": BRANCH} if self.branch_exists else None
        if method == "GET" and path == "/user":
            return {"login": self.actor}
        if method == "GET" and "/contents/" in path:
            if self.bytes is None:
                return None
            return {
                "type": "file", "sha": self.blob_sha,
                "content": base64.b64encode(self.bytes).decode("ascii"),
            }
        if method == "PUT" and "/contents/" in path:
            if self.reject_put:
                raise GitHubSaveError("conflict")
            if (data.get("sha") if data else None) != self.blob_sha:
                raise GitHubSaveError("optimistic concurrency conflict")
            self.bytes = base64.b64decode(data["content"], validate=True)
            self.commits += 1
            self.blob_sha = f"fake-blob-{self.commits}"
            return {
                "commit": {"sha": f"fake-commit-{self.commits}"},
                "content": {"sha": self.blob_sha},
            }
        raise AssertionError(f"unexpected request {method} {path}")


class TestPublicGitHubSaves(unittest.TestCase):
    def receipt(self, campaign, folder):
        save = Path("runtime") / (campaign + ".json")
        receipt = create_receipt(
            save_path=save, account_id="Aggredicus",
            repository=REPOSITORY, visibility="public", storage_choice="public",
            publication_understood=True, rules_and_compute_accepted=True,
            agreement_accepted=True, age_18_or_older=True,
        )
        p = Path(folder) / "local-consent.json"
        write_receipt(p, receipt)
        return p

    def play(self, api, receipt, campaign="test_public_alpha", **overrides):
        values = dict(
            campaign=campaign, mod_path=MOD, action="Inspect the cargo seal.",
            idempotency_key="turn-1", consent_path=str(receipt),
            confirm_first_publication=True,
        )
        values.update(overrides)
        return run_turn(api, **values)

    def test_preview_discloses_fields_and_does_not_publish(self):
        result = public_preview("test_public_alpha", MOD)
        self.assertEqual(result["status"], "preview_only")
        self.assertFalse(result["published"])
        self.assertIn("rng_streams", result["public_json_top_level_fields"])
        self.assertIn("event_ledger", result["public_json_top_level_fields"])
        self.assertNotIn("last_scene_packet", result["public_json_top_level_fields"])
        self.assertTrue(result["reconstructed_on_load"])
        self.assertEqual(result["branch"], BRANCH)
        self.assertEqual(result["codespaces"], "disabled; not used by this command")

    def test_invalid_campaign_is_rejected(self):
        for name in ("../private", "BigName", "a/b", ".env", "", "a"*49):
            with self.subTest(name=name):
                with self.assertRaises(GitHubSaveError):
                    remote_path(name)

    def test_missing_consent_blocks_without_remote_calls(self):
        api = FakeGitHub()
        with self.assertRaises(Exception):
            self.play(api, Path("/no/such/receipt.json"))
        self.assertFalse(api.requests)
        self.assertEqual(api.commits, 0)

    def test_first_publication_is_separately_confirmed(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FakeGitHub()
            receipt = self.receipt("test_public_alpha", folder)
            with self.assertRaisesRegex(GitHubSaveError, "confirm-first-publication"):
                self.play(api, receipt, confirm_first_publication=False)
            self.assertEqual(api.commits, 0)

    def test_identity_and_visibility_verified_before_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            receipt = self.receipt("test_public_alpha", folder)
            api = FakeGitHub()
            api.private = True
            with self.assertRaisesRegex(GitHubSaveError, "PUBLIC"):
                self.play(api, receipt)
            self.assertEqual(api.commits, 0)
            api = FakeGitHub()
            api.actor = "different-account"
            with self.assertRaisesRegex(GitHubSaveError, "login"):
                self.play(api, receipt)
            self.assertEqual(api.commits, 0)
            api = FakeGitHub()
            api.branch_exists = False
            with self.assertRaisesRegex(GitHubSaveError, "branch"):
                self.play(api, receipt)
            self.assertEqual(api.commits, 0)

    def test_authoritative_save_resumes_and_retries_are_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FakeGitHub()
            receipt = self.receipt("test_public_alpha", folder)
            first = self.play(api, receipt)
            self.assertTrue(first["persisted"])
            self.assertTrue(first["remote_verified"])
            self.assertEqual(first["turn"], 1)
            self.assertEqual(api.commits, 1)
            saved = decode_state(api.bytes)
            self.assertEqual(saved["github_publication"]["path"], remote_path("test_public_alpha"))
            self.assertTrue(verify_ledger(saved))
            self.assertNotIn("acknowledgements", saved)
            duplicate = self.play(api, receipt, confirm_first_publication=False)
            self.assertEqual(duplicate["status"], "duplicate")
            self.assertEqual(duplicate["turn"], 1)
            self.assertEqual(api.commits, 1)
            second = self.play(
                api, receipt, action="Request a telemetry report.",
                idempotency_key="turn-2", confirm_first_publication=False,
            )
            self.assertEqual(second["turn"], 2)
            self.assertEqual(api.commits, 2)
            saved2 = decode_state(api.bytes)
            self.assertEqual(saved2["state_version"], 2)
            self.assertTrue(verify_ledger(saved2))
            self.assertEqual(len(saved2["event_ledger"]), 3)

    def test_remote_conflict_does_not_claim_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FakeGitHub()
            receipt = self.receipt("test_public_alpha", folder)
            api.reject_put = True
            with self.assertRaisesRegex(GitHubSaveError, "conflict"):
                self.play(api, receipt)
            self.assertEqual(api.commits, 0)

    def test_state_does_not_include_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FakeGitHub()
            receipt = self.receipt("test_public_alpha", folder)
            with self.assertRaisesRegex(GitHubSaveError, "credential"):
                self.play(api, receipt, action="my key github_pat_" + "a" * 20)
            self.assertEqual(api.commits, 0)
            self.play(api, receipt)
            self.assertNotIn(b"fixture-not-real", api.bytes)
            self.assertNotIn(b"account_id", api.bytes)

    def test_tampered_remote_ledger_is_rejected_without_new_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FakeGitHub()
            receipt = self.receipt("test_public_alpha", folder)
            self.play(api, receipt)
            state = json.loads(api.bytes)
            state["event_ledger"][0]["hash"] = "tampered"
            api.bytes = json.dumps(state).encode("utf-8")
            with self.assertRaisesRegex(GitHubSaveError, "ledger"):
                self.play(api, receipt, idempotency_key="turn-2")
            self.assertEqual(api.commits, 1)



    def test_scene_is_stored_only_once_and_reconstructed(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FakeGitHub()
            receipt = self.receipt("test_public_alpha", folder)
            self.play(api, receipt)
            raw = json.loads(api.bytes)
            self.assertNotIn("last_scene_packet", raw)
            self.assertIn("scene_packet", raw["event_ledger"][-1]["payload"])
            revived = decode_state(api.bytes)
            self.assertEqual(
                revived["last_scene_packet"],
                revived["event_ledger"][-1]["payload"]["scene_packet"],
            )
            self.assertEqual(encode_state(revived), api.bytes)

    def test_legacy_pretty_save_retains_full_scene_on_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FakeGitHub()
            receipt = self.receipt("test_public_alpha", folder)
            self.play(api, receipt)
            revived = decode_state(api.bytes)
            legacy = json.dumps(revived, indent=2, ensure_ascii=False).encode("utf-8")
            same = decode_state(legacy)
            self.assertEqual(same, revived)
            self.assertEqual(same["last_scene_packet"], revived["last_scene_packet"])

    def test_inconsistent_legacy_scene_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FakeGitHub()
            receipt = self.receipt("test_public_alpha", folder)
            self.play(api, receipt)
            old = decode_state(api.bytes)
            old["last_scene_packet"] = {"turn": 10000}
            with self.assertRaisesRegex(GitHubSaveError, "disagrees"):
                encode_state(old)
            raw = json.dumps(old).encode("utf-8")
            with self.assertRaisesRegex(GitHubSaveError, "inconsistent"):
                decode_state(raw)


if __name__ == "__main__":
    unittest.main()
