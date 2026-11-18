import json
import tempfile
import unittest
from pathlib import Path

from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from fleet import FleetManager
from technology import TechnologyManager

class TechnologyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.catalog=Path(__file__).parents[1]/"technology"/"technology_tree.json"
        self.save=Path(self.temp.name)/"progress.json"
        self.resources=ResourceManager()
        self.tech=TechnologyManager(self.resources,self.catalog,self.save)

    def tearDown(self):
        self.temp.cleanup()

    def test_catalog_has_seven_branches_and_unique_complete_ids(self):
        data=json.loads(self.catalog.read_text(encoding="utf-8"))
        self.assertEqual(len(data["branches"]),7)
        ids=[t["id"] for t in data["technologies"]]
        self.assertEqual(len(ids),len(set(ids)))
        for tech in data["technologies"]:
            for field in ("name","description","icon","science_cost","prerequisites","bonuses","state"):
                self.assertIn(field,tech)

    def test_research_spends_science_completes_and_unlocks_dependency(self):
        before=self.resources.get("science").amount
        ok,_=self.tech.start_research("energy_01")
        self.assertTrue(ok)
        self.assertEqual(self.resources.get("science").amount,before-65)
        self.tech.update(18)
        self.assertEqual(self.tech.get("energy_01")["state"],"completed")
        self.assertEqual(self.tech.get("energy_02")["state"],"available")
        self.assertIsNone(self.tech.active_research)

    def test_only_one_research_can_run(self):
        self.assertTrue(self.tech.start_research("energy_01")[0])
        ok,_=self.tech.start_research("mining_01")
        self.assertFalse(ok)

    def test_progress_persists_as_json(self):
        self.tech.start_research("energy_01")
        self.tech.update(5)
        saved=json.loads(self.save.read_text(encoding="utf-8"))
        self.assertEqual(saved["active_research"],"energy_01")
        loaded=TechnologyManager(self.resources,self.catalog,self.save)
        self.assertEqual(loaded.active_research["technology_id"],"energy_01")
        self.assertAlmostEqual(loaded.active_research["elapsed"],5)

    def test_energy_technology_changes_economy_rates(self):
        buildings=BuildingManager(self.resources)
        self.tech.start_research("energy_01")
        self.tech.update(18)
        before=self.resources.get("energy").production
        buildings.set_technology_bonuses(self.tech.bonuses)
        self.assertAlmostEqual(self.resources.get("energy").production,before*1.12)

    def test_engineering_changes_build_time_and_cost(self):
        buildings=BuildingManager(self.resources)
        buildings.set_technology_bonuses({"construction_time_multiplier":0.5,
                                          "building_cost_multiplier":0.9})
        ok,_=buildings.start_build("solar_array")
        self.assertTrue(ok)
        self.assertAlmostEqual(buildings.constructions[-1].duration,6.0)

    def test_mining_technology_changes_actual_extraction_rate(self):
        mining=MiningManager(self.resources,initial_ship_count=1)
        ship=mining.ships[0]
        asteroid=mining.asteroids["asteroid_alpha"]
        ship.x,ship.y=asteroid.x,asteroid.y
        ship.task="mining"
        ship.target_id=asteroid.id
        mining.set_technology_bonuses({"mining_rate_multiplier":1.5})
        before=ship.cargo
        mining.update(1.0)
        self.assertAlmostEqual(ship.cargo-before,ship.mining_rate*1.5)

    def test_spaceflight_technology_changes_new_ship_speed(self):
        buildings=BuildingManager(self.resources)
        buildings.owned["hangar"]=[{"level":1,"instance_id":"hangar-test"}]
        mining=MiningManager(self.resources,initial_ship_count=0)
        fleet=FleetManager(self.resources,buildings,mining)
        fleet.set_technology_bonuses({"ship_speed_multiplier":1.2})
        ok,_=fleet.build_ship("scout")
        self.assertTrue(ok)
        fleet.update(22)
        scout=fleet.ships[0]
        self.assertAlmostEqual(scout.speed,190*1.2)

    def test_colonization_and_ai_bonus_values_are_aggregated(self):
        # All bonus definitions are consumed by the relevant simulation manager.
        self.assertIn("ship_cargo_multiplier",self.tech.bonuses)
        self.assertIn("maintenance_multiplier",self.tech.bonuses)
        self.assertIn("research_speed_multiplier",self.tech.bonuses)


    def test_technology_changes_colonizer_cargo_and_ship_hull(self):
        buildings=BuildingManager(self.resources)
        buildings.owned["hangar"]=[{"level":1,"instance_id":"hangar-test"}]
        mining=MiningManager(self.resources,initial_ship_count=0)
        fleet=FleetManager(self.resources,buildings,mining)
        fleet.set_technology_bonuses({"ship_hull_multiplier":1.2,
                                      "ship_cargo_multiplier":1.1,
                                      "colonization_bonus_multiplier":1.3})
        ok,_=fleet.build_ship("colonizer")
        self.assertTrue(ok)
        fleet.update(60)
        ship=fleet.ships[0]
        self.assertAlmostEqual(ship.max_hull,240*1.2)
        self.assertAlmostEqual(ship.cargo_capacity,180*1.1*1.3)

    def test_technology_changes_habitat_output_and_storage_capacity(self):
        buildings=BuildingManager(self.resources)
        buildings.owned["habitat"]=[{"level":1,"instance_id":"hab-01"}]
        base_credits=self.resources.get("credits").production
        base_metal_capacity=self.resources.get("metal").capacity
        buildings.set_technology_bonuses({"habitation_bonus_multiplier":1.5,
                                          "storage_capacity_multiplier":1.2})
        self.assertAlmostEqual(self.resources.get("credits").production,
                               base_credits+0.75*1.5)
        self.assertAlmostEqual(self.resources.get("metal").capacity,
                               base_metal_capacity*1.2)

    def test_invalid_delta_time(self):
        with self.assertRaises(ValueError):
            self.tech.update(-1)

if __name__=="__main__":
    unittest.main()
