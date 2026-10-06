import unittest
from phenomenal_engine.probability import logistic_success_probability, hazard_probability, BetaBelief
from phenomenal_engine.rng import PCG32

class TestProbability(unittest.TestCase):
    def test_logistic_center(self):
        self.assertAlmostEqual(logistic_success_probability(1,1, floor=0, ceiling=1), 0.5)

    def test_hazard(self):
        self.assertEqual(hazard_probability(0, 100), 0)
        self.assertGreater(hazard_probability(0.1, 10), 0.6)

    def test_bayes(self):
        b = BetaBelief()
        b.update(True); b.update(True); b.update(False)
        self.assertAlmostEqual(b.mean, 3/5)

if __name__ == "__main__":
    unittest.main()
