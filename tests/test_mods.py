import unittest
from pathlib import Path
from phenomenal_engine.mod_loader import load_mod

class TestMods(unittest.TestCase):
    def test_all_mods(self):
        base = Path(__file__).resolve().parents[1]
        mods = list((base / "mods").glob("*.json"))
        self.assertEqual(len(mods), 3)
        for path in mods:
            self.assertTrue(load_mod(path)["title"])

if __name__ == "__main__":
    unittest.main()
