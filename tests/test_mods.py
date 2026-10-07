import unittest
from pathlib import Path
from phenomenal_engine.mod_loader import load_mod


class TestMods(unittest.TestCase):
    def test_all_mods(self):
        base = Path(__file__).resolve().parents[1]
        mods = list((base / "mods").glob("*.json"))
        self.assertEqual(len(mods), 3)
        loaded = {path.name: load_mod(path) for path in mods}
        self.assertIn("mirror_delivery.json", loaded)
        self.assertNotIn("concord_tournament.json", loaded)
        self.assertEqual(loaded["mirror_delivery.json"]["title"], "Mirror Delivery")
        for mod in loaded.values():
            self.assertTrue(mod["title"])


if __name__ == "__main__":
    unittest.main()
