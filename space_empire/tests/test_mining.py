"""Automated tests for automated asteroid mining and fleet operations."""
import unittest
from economy import ResourceManager
from mining import MiningManager


class MiningManagerTests(unittest.TestCase):
    def setUp(self):
        self.resources = ResourceManager()
        self.mining = MiningManager(self.resources, initial_ship_count=1)

    def test_ship_dispatch_reserves_round_trip_fuel(self):
        ship = self.mining.ships[0]
        expected = self.mining._round_trip_fuel(ship, self.mining.asteroids[ship.target_id])
        self.assertEqual(ship.task, "outbound")
        self.assertAlmostEqual(self.resources.get("fuel").amount, 300.0 - expected)

    def test_complete_mining_cycle_delivers_metal(self):
        ship = self.mining.ships[0]
        self.mining.update(80.0)
        self.assertGreaterEqual(self.mining.delivered_total, 120.0)
        self.assertGreaterEqual(self.resources.get("metal").amount, 650.0)
        self.assertGreaterEqual(ship.cargo, 0.0)
        self.assertLessEqual(ship.cargo, ship.cargo_capacity)

    def test_fuel_never_becomes_negative_and_ship_waits_without_fuel(self):
        resources = ResourceManager()
        resources.get("fuel").amount = 0.0
        manager = MiningManager(resources, initial_ship_count=1)
        self.assertEqual(manager.ships[0].task, "docked")
        manager.update(10.0)
        self.assertEqual(resources.get("fuel").amount, 0.0)
        self.assertEqual(manager.ships[0].task, "docked")

    def test_ship_can_be_built_and_assigned(self):
        before = len(self.mining.ships)
        ok, _ = self.mining.build_ship()
        self.assertTrue(ok)
        self.assertEqual(len(self.mining.ships), before + 1)
        ship = self.mining.ships[-1]
        ok, _ = self.mining.assign_ship(ship.id, "asteroid_delta")
        self.assertTrue(ok)
        self.assertEqual(ship.assigned_target_id, "asteroid_delta")

    def test_upgrades_change_ship_statistics(self):
        ship = self.mining.ships[0]
        speed, capacity, rate = ship.speed, ship.cargo_capacity, ship.mining_rate
        self.assertTrue(self.mining.upgrade_ship(ship.id, "speed")[0])
        self.assertTrue(self.mining.upgrade_ship(ship.id, "capacity")[0])
        self.assertTrue(self.mining.upgrade_ship(ship.id, "mining")[0])
        self.assertGreater(ship.speed, speed)
        self.assertGreater(ship.cargo_capacity, capacity)
        self.assertGreater(ship.mining_rate, rate)

    def test_assignment_does_not_teleport_active_ship(self):
        ship = self.mining.ships[0]
        self.mining.update(1.0)
        old_x, old_y = ship.x, ship.y
        self.mining.assign_ship(ship.id, "asteroid_gamma")
        self.assertEqual((ship.x, ship.y), (old_x, old_y))
        self.assertEqual(ship.target_id, "asteroid_alpha")
        self.assertEqual(ship.assigned_target_id, "asteroid_gamma")

    def test_automatic_dispatch_respects_fuel_reserve(self):
        resources=ResourceManager()
        manager=MiningManager(resources,initial_ship_count=0)
        ship=manager._create_ship()
        manager.dispatch_fuel_reserve=resources.get("fuel").amount
        fuel_before=resources.get("fuel").amount
        manager._dispatch_docked_ships()
        self.assertEqual(ship.task,"docked")
        self.assertEqual(resources.get("fuel").amount,fuel_before)

    def test_automatic_dispatch_can_be_paused(self):
        manager=MiningManager(ResourceManager(),initial_ship_count=0)
        manager.auto_dispatch_enabled=False
        manager.build_ship()
        ship=manager.ships[0]
        manager.update(100)
        self.assertEqual(ship.task,"docked")

    def test_invalid_delta_time_is_rejected(self):
        with self.assertRaises(ValueError):
            self.mining.update(-0.5)


if __name__ == "__main__":
    unittest.main()
