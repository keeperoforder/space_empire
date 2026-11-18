import unittest
from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from fleet import FleetManager, Spaceship
from galaxy import GalaxyManager
from colonies import ColonyManager
from automation import TradeManager, AutomationManager

class AutomationTradeTests(unittest.TestCase):
    def setUp(self):
        self.economy=ResourceManager()
        self.buildings=BuildingManager(self.economy)
        self.mining=MiningManager(self.economy,initial_ship_count=0)
        self.fleet=FleetManager(self.economy,self.buildings,self.mining)
        self.galaxy=GalaxyManager(self.economy)
        self.colonies=ColonyManager(self.galaxy,self.fleet,self.economy)
        self.trade=TradeManager(self.economy,self.fleet,self.colonies)
        self.automation=AutomationManager(self.economy,self.buildings,self.mining,self.fleet,self.colonies,self.trade)

    def test_market_buy_and_sell_respect_stock_and_credits(self):
        before=self.economy.get("metal").amount
        ok,_=self.trade.buy("metal",25)
        self.assertTrue(ok)
        self.assertEqual(self.economy.get("metal").amount,before+25)
        ok,_=self.trade.sell("metal",10)
        self.assertTrue(ok)
        self.assertEqual(self.economy.get("metal").amount,before+15)
        self.assertFalse(self.trade.sell("metal",10**9)[0])

    def test_market_buy_rejects_full_storage_without_charging(self):
        resource=self.economy.get("metal")
        resource.amount=resource.capacity
        credits=self.economy.get("credits").amount
        ok,_=self.trade.buy("metal",1)
        self.assertFalse(ok)
        self.assertEqual(self.economy.get("credits").amount,credits)

    def test_auto_fuel_refills_from_market_when_enabled(self):
        self.economy.get("fuel").amount=0
        before=self.economy.get("fuel").amount
        self.automation.update(1)
        self.assertGreater(self.economy.get("fuel").amount,before)

    def test_automation_switches_are_independent_and_persist(self):
        self.automation.set_enabled("auto_build",True)
        self.automation.set_enabled("colonies",True)
        self.assertTrue(self.automation.settings["auto_build"]["enabled"])
        self.assertTrue(self.automation.settings["colonies"]["enabled"])
        snap=self.automation.snapshot()
        other=AutomationManager(self.economy,self.buildings,self.mining,self.fleet,self.colonies,self.trade)
        other.restore(snap)
        self.assertTrue(other.settings["auto_build"]["enabled"])
        self.assertTrue(other.settings["colonies"]["enabled"])

    def test_auto_build_obeys_rule_threshold_and_resources(self):
        self.economy.get("energy").amount=100
        self.automation.settings["auto_build"]["enabled"]=True
        self.automation.settings["auto_build"]["rules"]=[{"building_id":"solar_array","resource":"energy","below":150,"priority":1}]
        self.automation.update(1)
        self.assertEqual(len(self.buildings.constructions),1)

    def test_extensible_recipe_consumes_inputs_and_produces_outputs(self):
        self.automation.register_recipe("alloy_test",{"metal":10,"energy":5},{"crystals":2},duration=5,enabled=True)
        metal_before=self.economy.get("metal").amount
        crystal_before=self.economy.get("crystals").amount
        self.automation.update(5)
        self.assertEqual(self.economy.get("metal").amount,metal_before-10)
        self.assertEqual(self.economy.get("crystals").amount,crystal_before+2)
        self.assertEqual(self.automation.recipes["alloy_test"]["completed_batches"],1)

    def test_recipe_waits_for_output_storage_capacity(self):
        crystals=self.economy.get("crystals")
        crystals.amount=crystals.capacity
        self.automation.register_recipe("blocked_recipe",{"metal":10},{"crystals":1},duration=1,enabled=True)
        self.automation.update(1)
        recipe=self.automation.recipes["blocked_recipe"]
        self.assertTrue(recipe["running"])
        self.assertEqual(recipe["elapsed"],1)
        self.assertEqual(crystals.amount,crystals.capacity)

    def test_trade_route_requires_colonized_endpoints_and_transport(self):
        self.assertFalse(self.trade.create_route("missing-a","missing-b","metal",20,"ship")[0])

    def test_trade_route_dispatches_and_persists(self):
        planets=list(self.colonies.planets.values())[:2]
        for p in planets:
            self.colonies.colonies[p["id"]]={"planet_id":p["id"],"name":p["name"],"population":100,
                "development":1,"base_level":1,"base_built":True,
                "economy":{k:{"amount":200.0 if k=="metal" else 0.0,"capacity":1000.0,"production":0.0,"consumption":0.0}
                           for k in self.colonies.RESOURCE_KEYS},
                "transport_cooldown":0.0,"production_clock":0.0}
        self.buildings.owned["hangar"]=[{"level":1,"instance_id":"hangar-test"}]
        ok,_=self.fleet.build_ship("transport");self.assertTrue(ok)
        self.fleet.update(24)
        ship=next(s for s in self.fleet.ships if s.ship_type=="transport")
        ok,rid=self.trade.create_route(planets[0]["id"],planets[1]["id"],"metal",50,ship.id,interval=10)
        self.assertTrue(ok)
        route=self.trade.routes[0]
        self.trade.update(10)
        self.assertTrue(route["in_flight"])
        self.assertEqual(ship.metadata.get("trade_route_stage"),"to_source")
        self.assertEqual(self.colonies.colonies[planets[1]["id"]]["economy"]["metal"]["reserved_capacity"],50)
        snap=self.trade.snapshot()
        other=TradeManager(self.economy,self.fleet,self.colonies)
        other.restore(snap)
        self.assertEqual(other.routes[0]["id"],rid)
        self.assertTrue(other.routes[0]["in_flight"])
        destination=planets[1]["id"]
        initial=self.colonies.colonies[destination]["economy"]["metal"]["amount"]
        for _ in range(1200):
            self.fleet.update(1)
            self.trade.update(1)
            if not route["in_flight"]:break
        self.assertFalse(route["in_flight"])
        self.assertAlmostEqual(self.colonies.colonies[destination]["economy"]["metal"]["amount"],initial+50,places=4)
        self.assertNotIn("trade_route_id",ship.metadata)
        self.assertEqual(self.colonies.colonies[destination]["economy"]["metal"]["reserved_capacity"],0)

    def test_in_flight_route_can_be_disabled_but_still_settles(self):
        planets=list(self.colonies.planets.values())[:2]
        for p in planets:
            self.colonies.colonies[p["id"]]={"planet_id":p["id"],"name":p["name"],"population":100,
                "development":1,"base_level":1,"base_built":True,
                "economy":{k:{"amount":100.0 if k=="metal" else 0.0,"capacity":1000.0,"production":0.0,"consumption":0.0}
                           for k in self.colonies.RESOURCE_KEYS},
                "transport_cooldown":0.0,"production_clock":0.0}
        self.buildings.owned["hangar"]=[{"level":1,"instance_id":"hangar-test"}]
        self.fleet.build_ship("transport");self.fleet.update(24)
        ship=next(s for s in self.fleet.ships if s.ship_type=="transport")
        self.trade.create_route(planets[0]["id"],planets[1]["id"],"metal",20,ship.id,interval=10)
        route=self.trade.routes[0];self.trade.update(10)
        self.trade.toggle_route(route["id"],False)
        for _ in range(1200):
            self.fleet.update(1);self.trade.update(1)
            if not route["in_flight"]:break
        self.assertFalse(route["in_flight"])
        self.assertFalse(route["enabled"])

if __name__=="__main__":unittest.main()
