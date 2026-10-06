import unittest
from phenomenal_engine.rng import PCG32, derive_stream

class TestRNG(unittest.TestCase):
    def test_reproducible(self):
        a = PCG32(42, 7)
        b = PCG32(42, 7)
        self.assertEqual([a._next_uint32() for _ in range(20)], [b._next_uint32() for _ in range(20)])

    def test_state_restore(self):
        a = PCG32(99, 2)
        for _ in range(5): a.random()
        state = a.state_dict()
        b = PCG32.from_state_dict(state)
        self.assertEqual([a.random() for _ in range(5)], [b.random() for _ in range(5)])

    def test_substreams_differ(self):
        a = derive_stream("x", "weather")
        b = derive_stream("x", "combat")
        self.assertNotEqual(a.state_dict(), b.state_dict())

if __name__ == "__main__":
    unittest.main()
