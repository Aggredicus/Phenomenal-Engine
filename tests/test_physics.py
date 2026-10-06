import unittest
from phenomenal_engine.physics import sound_speed_air, planck_budget, light_wavelength, C

class TestPhysics(unittest.TestCase):
    def test_sound_speed(self):
        self.assertTrue(340 < sound_speed_air(20) < 345)

    def test_light(self):
        self.assertAlmostEqual(light_wavelength(C / 500e-9), 500e-9)

    def test_planck_budget(self):
        self.assertGreater(planck_budget()["log10_cell_updates"], 240)

if __name__ == "__main__":
    unittest.main()
