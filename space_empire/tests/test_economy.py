"""Automated tests for resource operations; run with python -m unittest discover -v."""
import math
import unittest
from economy import Resource, ResourceManager


class ResourceTests(unittest.TestCase):
    def test_add_respects_capacity_and_returns_accepted_amount(self):
        r = Resource("ore", "Ore", 8, 10)
        self.assertEqual(r.add(5), 2)
        self.assertEqual(r.amount, 10)

    def test_spend_is_safe(self):
        r = Resource("ore", "Ore", 5, 10)
        self.assertFalse(r.spend(6))
        self.assertEqual(r.amount, 5)
        self.assertTrue(r.spend(5))
        self.assertEqual(r.amount, 0)

    def test_invalid_values_are_rejected(self):
        for value in (-1, math.inf, math.nan):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Resource("ore", "Ore", 0, 10).add(value)

    def test_delta_time_production_and_consumption(self):
        r = Resource("energy", "Energy", 10, 100, production=5, consumption=2)
        r.update(2)
        self.assertAlmostEqual(r.amount, 16)
        self.assertAlmostEqual(r.balance, 3)

    def test_stock_never_goes_negative_or_over_capacity(self):
        r = Resource("energy", "Energy", 1, 10, production=0, consumption=50)
        r.update(10)
        self.assertEqual(r.amount, 0)
        r.set_rates(production=100, consumption=0)
        r.update(10)
        self.assertEqual(r.amount, 10)

    def test_manager_transaction_is_atomic(self):
        manager = ResourceManager()
        before = manager.get("metal").amount
        self.assertFalse(manager.spend({"metal": 10, "crystals": 999999}))
        self.assertEqual(manager.get("metal").amount, before)
        self.assertTrue(manager.spend({"metal": 100, "energy": 20}))
        self.assertEqual(manager.get("metal").amount, before - 100)

    def test_manager_delta_time_and_rates(self):
        manager = ResourceManager()
        start = manager.get("energy").amount
        manager.update(2.5)
        self.assertAlmostEqual(manager.get("energy").amount, start + 3.8 * 2.5)

    def test_invalid_delta_time(self):
        manager = ResourceManager()
        for dt in (-0.1, math.inf, math.nan):
            with self.subTest(dt=dt):
                with self.assertRaises(ValueError):
                    manager.update(dt)


if __name__ == "__main__":
    unittest.main()
