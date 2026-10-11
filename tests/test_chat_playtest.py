"""End-to-end checks for the honest local playtest launcher."""
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
SCRIPT = ROOT / "scripts" / "chat_playtest.py"


class TestChatPlaytest(unittest.TestCase):
    def setUp(self):
        self.before = {p.name for p in RUNTIME.glob("mirror-test-*")} if RUNTIME.exists() else set()

    def tearDown(self):
        for p in RUNTIME.glob("mirror-test-*"):
            if p.name not in self.before and p.is_file():
                p.unlink()

    def run_launcher(self, text):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--new", "--once"],
            cwd=ROOT, input=text, capture_output=True, text=True, timeout=25, check=False,
        )

    def test_public_playtest_requires_explicit_acceptance(self):
        data = self.run_launcher("example/Phenomenal-Engine\nPUBLIC\nNO\n")
        self.assertEqual(data.returncode, 3, data.stderr)
        self.assertIn("No game turn was executed", data.stdout)

    def test_real_engine_turn_requires_consent_and_persists_locally(self):
        data = self.run_launcher(
            "example/Phenomenal-Engine\nPUBLIC\nYES\nYES\nYES\nYES\nlocal-fixture\n"
        )
        self.assertEqual(data.returncode, 0, data.stderr)
        self.assertIn("AUTHORITATIVE LOCAL TURN 1", data.stdout)
        self.assertIn("Verified local persistence: true", data.stdout)
        self.assertIn("Remote GitHub persistence: NOT enabled", data.stdout)
        saves = [p for p in RUNTIME.glob("mirror-test-*.json") if p.name not in self.before and not p.name.endswith(".consent.json")]
        self.assertEqual(len(saves), 1)
        state = json.loads(saves[0].read_text())
        self.assertEqual(state["turn"], 1)
        self.assertEqual(state["player_identity"]["name"], "Jun Zan")


if __name__ == "__main__":
    unittest.main()
