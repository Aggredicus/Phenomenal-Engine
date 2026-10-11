"""Tokenless proposal tests: no network, no GitHub writes, no local campaign files."""
import copy
import json
import unittest

from phenomenal_engine.engine import Engine
from phenomenal_engine.github_saves import (
    BRANCH, REPOSITORY, decode_state, encode_state, remote_path,
)
from phenomenal_engine.consent import covenant_digest
from phenomenal_engine.memory import new_memory, verify_ledger
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.turn_exchange import (
    TurnExchangeError, git_blob_sha, propose_turn,
)


class TurnExchangeTests(unittest.TestCase):
    CAMPAIGN = "fast_turn_fixture"
    MOD = "mirror_delivery"

    def setUp(self):
        self.mod = load_mod("mods/mirror_delivery.json")
        state = new_memory(self.mod, "fast-turn-seed")
        state["github_publication"] = {
            "repository": REPOSITORY, "branch": BRANCH,
            "path": remote_path(self.CAMPAIGN),
            "public": True, "agreement_version": "DRAFT-0.1",
            "agreement_sha256": covenant_digest(),
        }
        Engine(self.mod, state).step(
            "I receive the mission briefing.",
            idempotency_key="turn-001",
        )
        raw = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        self.request = {
            "campaign_id": self.CAMPAIGN, "mod_id": self.MOD,
            "expected_state_version": 1,
            "expected_blob_sha": git_blob_sha(raw.encode("utf-8")),
            "save_json": raw,
            "action": "I inspect the ship and review the other crews.",
            "idempotency_key": "turn-002",
        }

    def test_no_token_required_and_no_fake_publication(self):
        req_before = copy.deepcopy(self.request)
        result = propose_turn(self.request)
        self.assertEqual(req_before, self.request)
        self.assertEqual(result["status"], "proposal")
        self.assertFalse(result["persisted"])
        self.assertFalse(result["remote_verified"])
        self.assertTrue(result["requires_write"])
        self.assertEqual(result["new_turn"], 2)
        self.assertEqual(result["state_version"], 2)
        self.assertEqual(result["expected_blob_sha"], self.request["expected_blob_sha"])
        self.assertEqual(result["proposed_blob_sha"], git_blob_sha(result["proposed_save_json"].encode("utf-8")))
        state = decode_state(result["proposed_save_json"].encode("utf-8"))
        self.assertTrue(verify_ledger(state))
        self.assertEqual(state["turn"], 2)
        self.assertEqual(state["last_scene_packet"]["turn"], 2)
        self.assertEqual(state["event_ledger"][-1]["payload"]["idempotency_key"], "turn-002")
        self.assertEqual(state["github_publication"]["path"], remote_path(self.CAMPAIGN))

    def test_compact_save_is_smaller_and_preserves_all_fields(self):
        result = propose_turn(self.request)
        raw = result["proposed_save_json"]
        state = decode_state(raw.encode("utf-8"))
        packed = {k: v for k, v in state.items() if k != "last_scene_packet"}
        self.assertEqual(raw, json.dumps(packed, ensure_ascii=False, separators=(",", ":")) + "\n")
        pretty = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        self.assertLess(len(raw.encode("utf-8")), len(pretty.encode("utf-8")) * 0.60)
        self.assertEqual(json.loads(raw), packed)
        self.assertEqual(state["last_scene_packet"], state["event_ledger"][-1]["payload"]["scene_packet"])

    def test_duplicate_does_not_run_again(self):
        result = propose_turn(self.request)
        req = copy.deepcopy(self.request)
        req.update(
            expected_state_version=2,
            save_json=result["proposed_save_json"],
            expected_blob_sha=result["proposed_blob_sha"],
        )
        duplicate = propose_turn(req)
        self.assertEqual(duplicate["status"], "duplicate")
        self.assertFalse(duplicate["persisted"])  # Python never attests to a remote write
        self.assertFalse(duplicate["remote_verified"])
        self.assertFalse(duplicate["requires_write"])
        self.assertEqual(duplicate["turn"], 2)
        self.assertEqual(duplicate["scene_packet"]["action"], req["action"])

    def test_reused_key_with_different_action_refused(self):
        first = propose_turn(self.request)
        req = dict(self.request, save_json=first["proposed_save_json"],
                   expected_blob_sha=first["proposed_blob_sha"],
                   expected_state_version=2, action="I fire the engine.")
        with self.assertRaisesRegex(TurnExchangeError, "different action"):
            propose_turn(req)

    def test_modified_bytes_are_rejected_before_rng(self):
        req = dict(self.request, save_json=self.request["save_json"] + " ")
        with self.assertRaisesRegex(TurnExchangeError, "blob SHA"):
            propose_turn(req)

    def test_stale_version_is_rejected(self):
        req = dict(self.request, expected_state_version=0)
        with self.assertRaisesRegex(TurnExchangeError, "state_version"):
            propose_turn(req)

    def test_wrong_mod_or_invalid_public_destination_is_rejected(self):
        with self.assertRaisesRegex(TurnExchangeError, "save/mod"):
            propose_turn(dict(self.request, mod_id="orbital_swarm_trail"))
        prior = json.loads(self.request["save_json"])
        prior["github_publication"]["branch"] = "main"
        new_raw = json.dumps(prior)
        wrong = dict(self.request, save_json=new_raw,
                     expected_blob_sha=git_blob_sha(new_raw.encode()))
        with self.assertRaisesRegex(TurnExchangeError, "public destination"):
            propose_turn(wrong)

    def test_injected_paths_keys_and_oversize_actions_refused(self):
        for bad in [
            {"campaign_id": "../private"},
            {"mod_id": "../private"},
            {"idempotency_key": "wrong space"},
            {"action": "x" * 2100},
            {"expected_blob_sha": "bad"},
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises((TurnExchangeError, ValueError)):
                    propose_turn(dict(self.request, **bad))


if __name__ == "__main__":
    unittest.main()
