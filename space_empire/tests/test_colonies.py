import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from fleet import FleetManager
from galaxy import GalaxyManager
from colonies import ColonyManager

class ColonyTests(unittest.TestCase):
    def setUp(self):
        self.economy=ResourceManager()
        for resource in self.economy.resources.values(): resource.amount=10000.0
        self.buildings=BuildingManager(self.economy)
        self.mining=MiningManager(self.economy, initial_ship_count=0)
        self.fleet=FleetManager(self.economy,self.buildings,self.mining)
        self.galaxy=GalaxyManager(self.economy)
        self.manager=ColonyManager(self.galaxy,self.fleet,self.economy)
        self.fleet.buildings.owned["hangar"]=[{"level":1,"instance_id":"test-hangar"}]
        self.fleet.build_ship("colonizer")
        self.fleet.update(61)
        self.fleet.build_ship("transport")
        self.fleet.update(25)

    def _planet(self, planet_type=None):
        self.manager.refresh_discoveries()
        planets=[p for p in self.manager.planets.values() if p["discovered"] and p["type"]!="gas_giant"]
        if planet_type:
            p=next(p for p in planets if p["type"]==planet_type)
        else:p=planets[0]
        return p

    def test_six_types_and_unique_planet_ids(self):
        self.assertEqual(set(self.manager.types),{"desert","ice","forest","volcanic","gas_giant","terrestrial"})
        ids=list(self.manager.planets)
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(all(p["id"] and p["name"] and p["size"]>0 for p in self.manager.planets.values()))

    def test_planet_unlock_tracks_galaxy_discovery(self):
        self.manager.refresh_discoveries()
        self.assertTrue(any(p["discovered"] for p in self.manager.planets.values()))
        self.assertTrue(any(not p["discovered"] for p in self.manager.planets.values()))

    def test_gas_giant_rejects_ground_colony(self):
        gas=next(p for p in self.manager.planets.values() if p["type"]=="gas_giant")
        gas["discovered"]=True
        ok,msg=self.manager.colonize(gas["id"])
        self.assertFalse(ok)
        self.assertIn("Газові",msg)

    def test_colonization_mission_founds_colony(self):
        p=self._planet()
        ok,_=self.manager.colonize(p["id"])
        self.assertTrue(ok)
        ship=next(s for s in self.fleet.ships if s.ship_type=="colonizer")
        # Advance until arrival at the working state.
        for _ in range(300): 
            self.fleet.update(1)
            self.manager.update(1)
            if p["id"] in self.manager.colonies:break
        self.assertIn(p["id"],self.manager.colonies)
        self.assertTrue(p["colonized"])

    def test_base_starts_local_production(self):
        p=self._planet()
        self.manager.colonies[p["id"]]={"planet_id":p["id"],"name":p["name"],"population":100,"development":1,"base_level":0,"base_built":False,
            "economy":{k:{"amount":0.0,"capacity":1000.0,"production":0.0,"consumption":0.0} for k in self.manager.RESOURCE_KEYS},"transport_cooldown":0.0,"production_clock":0.0}
        ok,_=self.manager.build_base(p["id"])
        self.assertTrue(ok)
        self.manager.update(10)
        self.assertGreater(self.manager.colonies[p["id"]]["economy"]["metal"]["amount"],0)

    def test_colony_transport_delivers_local_stock_to_station(self):
        p=self._planet()
        colony={"planet_id":p["id"],"name":p["name"],"population":100,"development":1,"base_level":1,"base_built":True,
            "economy":{k:{"amount":250.0 if k=="metal" else 0.0,"capacity":1000.0,"production":0.0,"consumption":0.0} for k in self.manager.RESOURCE_KEYS},"transport_cooldown":0.0,"production_clock":0.0}
        self.manager.colonies[p["id"]]=colony
        transports=[s for s in self.fleet.ships if s.ship_type=="transport"]
        self.assertTrue(transports)
        ok,_=self.manager.transfer_to_station(p["id"],transports[0].id,"metal",100)
        self.assertTrue(ok)
        before=self.economy.get("metal").amount
        for _ in range(20):
            self.fleet.update(1)
            self.manager.update(1)
        self.assertGreater(self.economy.get("metal").amount,before)

    def test_colony_transfer_respects_station_storage_capacity(self):
        p=self._planet()
        colony={"planet_id":p["id"],"name":p["name"],"population":100,"development":1,"base_level":1,"base_built":True,
            "economy":{k:{"amount":250.0 if k=="metal" else 0.0,"capacity":1000.0,"production":0.0,"consumption":0.0} for k in self.manager.RESOURCE_KEYS},"transport_cooldown":0.0,"production_clock":0.0}
        self.manager.colonies[p["id"]]=colony
        transport=next(s for s in self.fleet.ships if s.ship_type=="transport")
        self.economy.get("metal").amount=self.economy.get("metal").capacity
        ok,msg=self.manager.transfer_to_station(p["id"],transport.id,"metal",100)
        self.assertFalse(ok)
        self.assertIn("місця",msg)

    def test_snapshot_restore(self):
        p=self._planet()
        snap=self.manager.snapshot()
        other=ColonyManager(self.galaxy,self.fleet,self.economy)
        other.restore(snap)
        self.assertEqual(other.planets[p["id"]],self.manager.planets[p["id"]])

if __name__=="__main__":unittest.main()
