"""Automated tests for station construction and economy integration."""
import unittest
from economy import ResourceManager
from buildings import BuildingManager


class BuildingManagerTests(unittest.TestCase):
    def setUp(self):
        self.resources = ResourceManager()
        self.buildings = BuildingManager(self.resources)

    def test_catalog_contains_ten_unique_building_ids(self):
        self.assertEqual(len(self.buildings.catalog), 10)
        self.assertEqual(len(set(self.buildings.catalog)), 10)
        self.assertEqual(self.buildings.count("core"), 1)

    def test_build_cost_is_paid_and_effect_activates_on_completion(self):
        energy_before = self.resources.get("energy").production
        metal_before = self.resources.get("metal").amount
        ok, _ = self.buildings.start_build("solar_array")
        self.assertTrue(ok)
        self.assertEqual(self.resources.get("metal").amount, metal_before - 90)
        self.assertEqual(self.resources.get("energy").production, energy_before)
        self.buildings.update(11.9)
        self.assertEqual(self.buildings.count("solar_array"), 0)
        self.buildings.update(0.1)
        self.assertEqual(self.buildings.count("solar_array"), 1)
        self.assertAlmostEqual(self.resources.get("energy").production, energy_before + 8.0)

    def test_unaffordable_build_does_not_deduct_resources(self):
        before = self.resources.snapshot()
        self.resources.get("metal").amount = 0
        after_zero = self.resources.get("energy").amount
        ok, _ = self.buildings.start_build("smelter")
        self.assertFalse(ok)
        self.assertEqual(self.resources.get("energy").amount, after_zero)

    def test_upgrade_cost_scales_and_level_effect_increases(self):
        ok, _ = self.buildings.start_build("solar_array")
        self.assertTrue(ok)
        self.buildings.update(12)
        before = self.resources.get("energy").production
        cost = self.buildings.next_upgrade_cost("solar_array")
        self.assertGreater(cost["metal"], self.buildings.definition("solar_array")["cost"]["metal"])
        ok, _ = self.buildings.start_upgrade("solar_array")
        self.assertTrue(ok)
        self.buildings.update(self.buildings.upgrade_time("solar_array"))
        self.assertEqual(self.buildings.instances("solar_array")[0]["level"], 2)
        self.assertAlmostEqual(self.resources.get("energy").production, before + 8.0 * 0.55)

    def test_storage_building_increases_capacity_after_completion(self):
        capacity_before = self.resources.get("metal").capacity
        ok, _ = self.buildings.start_build("warehouse")
        self.assertTrue(ok)
        self.buildings.update(self.buildings.definition("warehouse")["build_time"])
        self.assertEqual(self.resources.get("metal").capacity, capacity_before + 900)

    def test_projects_use_delta_time_and_reject_invalid_values(self):
        self.buildings.start_build("solar_array")
        self.buildings.update(6)
        self.assertAlmostEqual(self.buildings.progress_snapshot()[0]["progress"], 0.5)
        with self.assertRaises(ValueError):
            self.buildings.update(-1)


if __name__ == "__main__":
    unittest.main()
