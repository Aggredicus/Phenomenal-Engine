import unittest
from phenomenal_engine.rng import PCG32
from phenomenal_engine.game_theory import TitForTat, AlwaysCooperate, AlwaysDefect, play_match

class TestGameTheory(unittest.TestCase):
    def test_tft_cooperates_with_cooperator(self):
        r = play_match(TitForTat(), AlwaysCooperate(), 20, PCG32(1,2), error_rate=0)
        self.assertEqual(r["a_cooperation"], 1.0)

    def test_tft_retaliates(self):
        r = play_match(TitForTat(), AlwaysDefect(), 5, PCG32(1,2), error_rate=0)
        self.assertEqual(r["history"][0], "CD")
        self.assertTrue(all(x == "DD" for x in r["history"][1:]))

if __name__ == "__main__":
    unittest.main()
