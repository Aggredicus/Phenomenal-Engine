"""Read-only prelude guards and verified reveal requirements."""
import copy
import unittest

from phenomenal_engine.memory import new_memory, append_event
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.turn_streaming import (
    ALLOWED_PHASES, build_prelude_packet, phase_event, verified_reveal,
)


class TurnStreamingTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_mod("mods/mirror_delivery.json")
        self.state = new_memory(self.mod, "known-seed")
        self.state["turn"] = 1
        self.state["state_version"] = 1
        self.state["last_scene_packet"] = {"turn": 1, "phenomenology": {"auditory": "quiet"}}
        append_event(self.state, "player_action", {"action": "Briefing", "scene_packet": self.state["last_scene_packet"]})

    def test_prelude_does_not_mutate_known_state_or_consume_rng(self):
        before = copy.deepcopy(self.state)
        p = build_prelude_packet(self.mod, self.state, "Inspect ship and courier crews")
        self.assertEqual(self.state, before)
        self.assertFalse(p["authoritative"])
        self.assertFalse(p["persisted"])
        self.assertTrue(p["no_rng_consumed"])
        self.assertEqual(p["prior_turn"], 1)
        self.assertIn("Inspect ship", p["scene_lines"][-2])
        self.assertFalse(any("passed inspection" in x for x in p["scene_lines"]))

    def test_rejects_tampered_ledger(self):
        self.state["event_ledger"][0]["hash"] = "bad"
        with self.assertRaisesRegex(ValueError, "ledger"):
            build_prelude_packet(self.mod, self.state, "Review")

    def test_rejects_mismatched_last_scene(self):
        self.state["last_scene_packet"] = {"turn": 200}
        with self.assertRaisesRegex(ValueError, "disagree"):
            build_prelude_packet(self.mod, self.state, "Review")

    def test_phase_names_require_real_caller(self):
        self.assertIn("readback_verified", ALLOWED_PHASES)
        with self.assertRaises(ValueError):
            phase_event("everything_100_percent", state_version=1)
        self.assertEqual(phase_event("simulation_started", state_version=1)["authoritative_result"], False)

    def test_reveal_requires_proven_remote_write_and_scene(self):
        result = {
            "status": "ok", "persisted": True, "remote_verified": True,
            "turn": 2, "state_version": 2,
            "scene_packet": {"turn": 2, "action": "Review"},
            "repository": "Aggredicus/Phenomenal-Engine",
            "path": "campaigns/example.json", "commit_sha": "abc",
        }
        self.assertTrue(verified_reveal(result)["authoritative"])
        for bad in [
            {"persisted": False}, {"remote_verified": False},
            {"status": "error"}, {"scene_packet": {"turn": 1}},
            {"repository": ""}, {"path": ""},
        ]:
            with self.subTest(bad=bad):
                modified = dict(result, **bad)
                with self.assertRaises(ValueError):
                    verified_reveal(modified)


if __name__ == "__main__":
    unittest.main()
