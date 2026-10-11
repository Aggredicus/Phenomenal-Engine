import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from phenomenal_engine.cli import main
from phenomenal_engine.consent import (
    ConsentError, covenant_digest, create_receipt, default_receipt_path,
    load_receipt, verify_receipt, write_receipt,
)


class TestConsentGate(unittest.TestCase):
    def setUp(self):
        self.mod = str(Path(__file__).resolve().parents[1] / "mods" / "mirror_delivery.json")

    def invoke(self, args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                main(args)
            except SystemExit as e:
                return json.loads(buf.getvalue()), e.code
        return json.loads(buf.getvalue()), 0

    def make_receipt(self, save, visibility="public", choice="public"):
        return create_receipt(
            save_path=save, account_id="fixture-account",
            repository="example/game-save",
            visibility=visibility, storage_choice=choice,
            publication_understood=True, rules_and_compute_accepted=True,
            agreement_accepted=True, age_18_or_older=True,
        )

    def test_play_refuses_before_rng_or_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "state.json"
            result, exit_code = self.invoke([
                "play", self.mod, str(save), "Begin.",
                "--idempotency-key", "consent-denied",
            ])
            self.assertEqual(exit_code, 3)
            self.assertEqual(result["status"], "consent_required")
            self.assertFalse(result["persisted"])
            self.assertFalse(save.exists())

    def test_new_save_requires_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "state.json"
            result, exit_code = self.invoke(["new-save", self.mod, str(save)])
            self.assertEqual(exit_code, 3)
            self.assertFalse(save.exists())
            self.assertEqual(result["status"], "consent_required")

    def test_receipt_requires_matching_visibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "state.json"
            with self.assertRaises(ConsentError):
                self.make_receipt(save, "public", "private")

    def test_missing_acknowledgement_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "state.json"
            value = self.make_receipt(save)
            value["acknowledgements"]["publication_understood"] = False
            with self.assertRaises(ConsentError):
                verify_receipt(value, save_path=save)

    def test_revised_terms_force_new_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "state.json"
            value = self.make_receipt(save)
            value["agreement_sha256"] = "deadbeef"
            with self.assertRaises(ConsentError):
                verify_receipt(value, save_path=save)

    def test_receipt_is_bound_to_save_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "a.json"
            value = self.make_receipt(save)
            with self.assertRaises(ConsentError):
                verify_receipt(value, save_path=Path(tmp) / "b.json")

    def test_accepted_game_persists_and_duplicate_does_not_advance(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "state.json"
            receipt = self.make_receipt(save)
            write_receipt(default_receipt_path(save), receipt)
            key = "test-consent-unique-1"
            args = ["play", self.mod, str(save), "Inspect vault.", "--idempotency-key", key]
            result, status = self.invoke(args)
            self.assertEqual(status, 0)
            self.assertTrue(result["persisted"])
            duplicate, status = self.invoke(args)
            self.assertEqual(status, 0)
            self.assertEqual(duplicate["status"], "duplicate")
            self.assertEqual(duplicate["turn"], 1)

    def test_cli_does_not_claim_github_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "state.json"
            result, status = self.invoke([
                "accept-covenant", str(save), "--account-id", "test-id",
                "--repository", "example/game-save",
                "--visibility", "public", "--storage-choice", "public",
                "--publication-understood", "--rules-accepted", "--agree", "--adult",
            ])
            self.assertEqual(status, 0)
            self.assertEqual(result["status"], "accepted_locally_unverified")
            verified = load_receipt(default_receipt_path(save), save_path=save)
            self.assertEqual(verified["agreement_sha256"], covenant_digest())

    def test_cli_unchecked_flags_never_implicitly_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "state.json"
            result, status = self.invoke([
                "accept-covenant", str(save), "--account-id", "test-id",
                "--repository", "example/game-save",
                "--visibility", "public", "--storage-choice", "public",
            ])
            self.assertEqual(status, 3)
            self.assertFalse(default_receipt_path(save).exists())


if __name__ == "__main__":
    unittest.main()
