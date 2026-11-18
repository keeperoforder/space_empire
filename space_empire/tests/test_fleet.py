import unittest
from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from fleet import FleetManager, SHIP_TYPES

class FleetTests(unittest.TestCase):
    def setUp(self):
        self.resources=ResourceManager()
        self.buildings=BuildingManager(self.resources)
        self.mining=MiningManager(self.resources,initial_ship_count=0)
        self.fleet=FleetManager(self.resources,self.buildings,self.mining)

    def unlock_hangar(self):
        self.buildings.owned["hangar"]=[{"level":1,"instance_id":"hangar-test"}]

    def finish_build(self, kind):
        ok,_=self.fleet.build_ship(kind)
        self.assertTrue(ok)
        duration=SHIP_TYPES[kind]["build_time"]
        self.fleet.update(duration)
        return self.fleet.ships[-1]

    def test_all_seven_ship_definitions_are_distinct(self):
        self.assertEqual(len(SHIP_TYPES),7)
        self.assertEqual(len({v["shape"] for v in SHIP_TYPES.values()}),7)

    def test_hangar_required(self):
        ok,msg=self.fleet.build_ship("scout")
        self.assertFalse(ok)
        self.assertIn("ангар",msg.lower())

    def test_production_is_queued_and_charged(self):
        self.unlock_hangar()
        before=self.resources.get("metal").amount
        ok,_=self.fleet.build_ship("transport")
        self.assertTrue(ok)
        self.assertEqual(len(self.fleet.ships),0)
        self.assertLess(self.resources.get("metal").amount,before)
        self.fleet.update(23)
        self.assertEqual(len(self.fleet.ships),0)
        self.fleet.update(1)
        self.assertEqual(len(self.fleet.ships),1)
        self.assertEqual(self.fleet.ships[0].ship_type,"transport")

    def test_group_dispatch_and_return(self):
        self.unlock_hangar()
        ship=self.finish_build("scout")
        ok,gid=self.fleet.create_group("Alpha",[ship.id])
        self.assertTrue(ok)
        ok,_=self.fleet.dispatch_group(gid,"explore",30,0,"Сектор X",1)
        self.assertTrue(ok)
        self.fleet.update(10)
        self.assertEqual(ship.status,"ready")
        self.assertEqual((ship.x,ship.y),(0.0,0.0))

    def test_upgrade_changes_stats(self):
        self.unlock_hangar()
        ship=self.finish_build("fighter")
        speed=ship.speed
        ok,_=self.fleet.upgrade_ship(ship.id,"speed")
        self.assertTrue(ok)
        self.assertGreater(ship.speed,speed)
        self.assertEqual(ship.level,2)

    def test_miner_uses_existing_mining_manager(self):
        self.unlock_hangar()
        self.finish_build("miner")
        self.assertEqual(len(self.mining.ships),1)
        self.assertEqual(len([s for s in self.fleet.ships if s.ship_type=="miner"]),1)
        self.assertEqual(self.fleet.ships[0].linked_miner_id,self.mining.ships[0].id)


    def test_maintenance_failure_disables_ship_then_repairs_when_funded(self):
        self.unlock_hangar()
        ship=self.finish_build("fighter")
        self.resources.get("credits").amount=0
        self.fleet.update(2)
        self.assertEqual(ship.status,"maintenance")
        damaged=ship.hull
        self.resources.get("credits").amount=100
        self.fleet.update(10)
        self.assertGreater(ship.hull,damaged)

    def test_invalid_delta_time(self):
        with self.assertRaises(ValueError):
            self.fleet.update(-1)

if __name__=="__main__":
    unittest.main()
