import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from phenomenal_engine.cli import main


class TestStartupChoices(unittest.TestCase):
    def setUp(self):
        self.mods = Path(__file__).resolve().parents[1] / "mods"

    def start(self, *extra):
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["start", "--mods", str(self.mods), *extra])
        return json.loads(buf.getvalue())

    def test_default_suggests_but_does_not_enable_codespaces(self):
        data = self.start()
        self.assertEqual(data["status"], "setup_choices")
        self.assertEqual(data["runtime_policy"], "prefer_existing_trusted_runtime")
        self.assertEqual(len(data["mods"]), 3)
        choice = data["codespaces"]
        self.assertTrue(choice["optional"])
        self.assertFalse(choice["default_enabled"])
        self.assertEqual(choice["choice"], "offer")
        self.assertFalse(choice["created"])
        self.assertFalse(choice["requested"])
        self.assertTrue(choice["may_incur_charges"])
        self.assertIn("charges may apply", choice["prompt"])

    def test_opt_in_requires_separate_manual_action(self):
        data = self.start("--codespaces")
        choice = data["codespaces"]
        self.assertEqual(choice["choice"], "requested")
        self.assertTrue(choice["requested"])
        self.assertFalse(choice["created"])
        self.assertGreater(len(choice["setup_steps"]), 0)

    def test_decline_skips_offer(self):
        data = self.start("--no-codespaces")
        choice = data["codespaces"]
        self.assertEqual(choice["choice"], "off")
        self.assertIsNone(choice["prompt"])
        self.assertFalse(choice["created"])
        self.assertEqual(choice["setup_steps"], [])

    def test_start_creates_no_game_state(self):
        with tempfile.TemporaryDirectory() as temp:
            data = self.start("--mods", str(Path(temp) / "not-there"))
            self.assertFalse(Path(temp, "runtime").exists())
            self.assertEqual(data["mods"], [])
            self.assertFalse(data["codespaces"]["created"])


if __name__ == "__main__":
    unittest.main()
