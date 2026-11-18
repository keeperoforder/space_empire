import unittest
from types import SimpleNamespace

from galaxy import GalaxyManager


class FakeResources:
    def __init__(self):
        self.stock = {k: 0 for k in ("metal", "crystals", "fuel", "credits", "science")}
    def add(self, key, amount):
        self.stock[key] = self.stock.get(key, 0) + amount
        return amount


class FakeFleet:
    def __init__(self):
        self.ships = [SimpleNamespace(id="scout-1", ship_type="scout", status="ready",
                                      task="idle", speed=190.0, x=0.0, y=0.0,
                                      metadata={})]
        self.assignment = None
    def assign_task(self, ship_id, task, x, y, name, duration):
        self.assignment = (ship_id, task, x, y, name, duration)
        ship = self.ships[0]
        ship.status, ship.task = "outbound", task
        return True, "sent"


class GalaxyTests(unittest.TestCase):
    def setUp(self):
        self.resources = FakeResources()
        self.galaxy = GalaxyManager(self.resources)
        self.fleet = FakeFleet()

    def test_catalog_has_twenty_unique_systems_and_one_initial_discovery(self):
        self.assertEqual(len(self.galaxy.systems), 20)
        self.assertEqual(len(set(self.galaxy.systems)), 20)
        self.assertEqual(sum(s["discovered"] for s in self.galaxy.systems.values()), 1)
        object_types = {o["type"] for s in self.galaxy.systems.values() for o in s["objects"]}
        self.assertEqual(object_types, {"Планета", "Астероїдне поле", "Покинута станція", "Невідомий об'єкт"})

    def test_frontier_unlocks_only_next_to_discovered_system(self):
        self.assertTrue(self.galaxy.systems["vega"]["accessible"])
        self.assertFalse(self.galaxy.systems["castor"]["accessible"])

    def test_route_requires_accessible_destination(self):
        ok, _ = self.galaxy.plot_route("sol", "vega")
        self.assertTrue(ok)
        ok, _ = self.galaxy.plot_route("sol", "castor")
        self.assertFalse(ok)

    def test_expedition_requires_scout_and_returns_rewards_and_discovery(self):
        ok, _ = self.galaxy.launch_expedition(self.fleet, "vega")
        self.assertTrue(ok)
        self.assertIn("scout-1", self.galaxy.expeditions)
        ship = self.fleet.ships[0]
        ship.status, ship.task = "ready", "idle"
        self.galaxy.update(self.fleet)
        self.assertTrue(self.galaxy.systems["vega"]["discovered"])
        self.assertTrue(all(o["revealed"] for o in self.galaxy.systems["vega"]["objects"]))
        self.assertNotIn("scout-1", self.galaxy.expeditions)
        self.assertGreater(self.resources.stock["metal"], 0)
        self.assertEqual(len(self.galaxy.completed_expeditions), 1)
        metal_after = self.resources.stock["metal"]
        self.galaxy.update(self.fleet)
        self.assertEqual(self.resources.stock["metal"], metal_after)
        self.assertEqual(len(self.galaxy.completed_expeditions), 1)

    def test_expedition_cannot_be_launched_to_locked_system(self):
        ok, _ = self.galaxy.launch_expedition(self.fleet, "castor")
        self.assertFalse(ok)

    def test_expedition_does_not_complete_until_ship_returns_to_origin(self):
        self.galaxy.launch_expedition(self.fleet, "vega")
        ship = self.fleet.ships[0]
        ship.x, ship.y = 50.0, 20.0
        ship.status, ship.task = "ready", "idle"
        self.galaxy.update(self.fleet)
        self.assertFalse(self.galaxy.systems["vega"]["discovered"])
        self.assertEqual(ship.status, "returning")
        self.assertEqual(ship.target_x, 0.0)

    def test_expedition_estimate_includes_outbound_scan_and_return(self):
        expected = 2*self.galaxy.route_distance("sol","vega")/190.0 + 45.0
        self.assertAlmostEqual(self.galaxy.route_time("sol","vega",190.0,45.0),expected)

    def test_galaxy_progress_round_trips_through_snapshot(self):
        self.galaxy.systems["vega"]["discovered"] = True
        self.galaxy._refresh_accessibility()
        self.galaxy.plotted_routes.append({"from":"sol","to":"vega"})
        snapshot = self.galaxy.snapshot()
        other = GalaxyManager(FakeResources())
        other.restore(snapshot)
        self.assertTrue(other.systems["vega"]["discovered"])
        self.assertEqual(other.plotted_routes, self.galaxy.plotted_routes)


if __name__ == "__main__":
    unittest.main()
