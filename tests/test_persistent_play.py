import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from phenomenal_engine.cli import main
from phenomenal_engine.memory import load_memory


class TestPersistentPlay(unittest.TestCase):
    def setUp(self):
        self.base = Path(__file__).resolve().parents[1]
        self.mod = self.base / "mods" / "mirror_delivery.json"

    def run_cli(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(argv)
        return json.loads(buf.getvalue())

    def test_play_creates_and_continues_same_campaign(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "mirror.json"
            first = self.run_cli([
                "play", str(self.mod), str(save), "Inspect the sealed Mir vault.",
                "--seed", "persistent-test",
                "--idempotency-key", "turn-1",
            ])
            self.assertTrue(first["created"])
            self.assertTrue(first["persisted"])
            self.assertEqual(first["turn"], 1)
            campaign_id = first["campaign_id"]

            second = self.run_cli([
                "play", str(self.mod), str(save), "Ask Juno what she thinks of the mission.",
                "--idempotency-key", "turn-2",
            ])
            self.assertFalse(second["created"])
            self.assertEqual(second["turn"], 2)
            self.assertEqual(second["campaign_id"], campaign_id)

            memory = load_memory(save)
            self.assertEqual(memory["turn"], 2)
            self.assertEqual(memory["state_version"], 2)
            self.assertEqual(memory["session_id"], campaign_id)
            self.assertGreaterEqual(len(memory["event_ledger"]), 3)
            self.assertIsNotNone(memory["last_scene_packet"])
            self.assertIn("actions", memory["rng_streams"])

    def test_idempotency_key_prevents_duplicate_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "mirror.json"
            argv = [
                "play", str(self.mod), str(save), "Inspect the mission orders.",
                "--idempotency-key", "same-request",
            ]
            first = self.run_cli(argv)
            second = self.run_cli(argv)
            self.assertEqual(first["status"], "ok")
            self.assertEqual(second["status"], "duplicate")
            self.assertEqual(second["turn"], 1)
            memory = load_memory(save)
            self.assertEqual(memory["turn"], 1)

    def test_status_verifies_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "mirror.json"
            created = self.run_cli([
                "play", str(self.mod), str(save), "Begin.",
                "--idempotency-key", "status-turn",
            ])
            status = self.run_cli(["status", str(save)])
            self.assertEqual(status["campaign_id"], created["campaign_id"])
            self.assertEqual(status["turn"], 1)

    def test_tampered_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "mirror.json"
            self.run_cli([
                "play", str(self.mod), str(save), "Begin.",
                "--idempotency-key", "tamper-turn",
            ])
            raw = json.loads(save.read_text(encoding="utf-8"))
            raw["event_ledger"][-1]["payload"]["action"] = "tampered"
            save.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_memory(save)

    def test_new_save_does_not_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / "mirror.json"
            self.run_cli(["new-save", str(self.mod), str(save)])
            with self.assertRaises(FileExistsError):
                self.run_cli(["new-save", str(self.mod), str(save)])


if __name__ == "__main__":
    unittest.main()
