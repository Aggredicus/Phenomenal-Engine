"""Bounded regressions: reproducibility and restoring an odd Box-Muller draw."""
import unittest
from phenomenal_engine.rng import PCG32, derive_stream

class ReviewForgeRNGRegressions(unittest.TestCase):
    def test_wide_inclusive_ranges(self):
        for seed in range(40):
            for lo, hi in ((0, 1 << 32), (-(1 << 41), (1 << 41) + 7), (-(1 << 100), 1 << 100)):
                with self.subTest(seed=seed, lo=lo, hi=hi):
                    rng = PCG32(seed, 17)
                    values = [rng.randint(lo, hi) for _ in range(20)]
                    self.assertTrue(all(lo <= value <= hi for value in values))

    def test_wide_range_replay(self):
        a, b = PCG32(31415, 2), PCG32(31415, 2)
        self.assertEqual([a.randint(-(1 << 65), 1 << 65) for _ in range(100)],
                         [b.randint(-(1 << 65), 1 << 65) for _ in range(100)])

    def test_normal_cache_restore(self):
        a = derive_stream("reviewforge", "encounter")
        a.normal()
        state = a.state_dict()
        self.assertIsNotNone(state["normal_cache"])
        b = PCG32.from_state_dict(state)
        self.assertEqual([a.normal() for _ in range(20)], [b.normal() for _ in range(20)])
        self.assertEqual(a.state_dict(), b.state_dict())

    def test_old_rng_state_still_loads(self):
        a = PCG32(55, 4)
        state = a.state_dict()
        state.pop("normal_cache")
        self.assertEqual(a.random(), PCG32.from_state_dict(state).random())

    def test_oversized_integer_cache_is_rejected_as_invalid(self):
        # A valid JSON integer can exceed float range and must not leak OverflowError.
        state = PCG32(2, 3).state_dict()
        state["normal_cache"] = 1 << 4096
        with self.assertRaisesRegex(ValueError, "invalid PCG32 normal_cache"):
            PCG32.from_state_dict(state)

    def test_cached_normal_survives_json_roundtrip(self):
        import json
        original = PCG32(33, 7)
        original.normal()
        restored = PCG32.from_state_dict(json.loads(json.dumps(original.state_dict())))
        self.assertEqual([original.normal() for _ in range(20)],
                         [restored.normal() for _ in range(20)])

    def test_invalid_cache_rejected(self):
        for bad in ("garbage", float("nan"), float("inf"), {}, True):
            state = PCG32(2, 3).state_dict()
            state["normal_cache"] = bad
            with self.subTest(value=repr(bad)), self.assertRaises(ValueError):
                PCG32.from_state_dict(state)

if __name__ == "__main__":
    unittest.main()
