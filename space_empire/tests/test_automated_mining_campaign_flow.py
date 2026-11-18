"""End-to-end regression for the first real mining campaign dependency chain."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from campaign import CampaignManager
from progression import GameProgression

ROOT = Path(__file__).resolve().parents[1]


class _Technology:
    def __init__(self):
        self.technologies = {"ai_01": {"state": "locked"}}
        self.research_enabled = False

    def set_research_enabled(self, enabled):
        self.research_enabled = bool(enabled)


class AutomatedMiningCampaignFlowTests(unittest.TestCase):
    def test_fresh_campaign_builds_miner_and_delivers_real_asteroid_cargo(self):
        campaign_data = json.loads((ROOT / "campaign/campaign.json").read_text(encoding="utf-8"))
        missions = {m["id"]: m for m in campaign_data["missions"]}
        self.assertEqual(missions["mine"]["objective"], {"type": "mining_ship", "amount": 1})
        self.assertEqual(missions["miner"]["objective"], {"type": "mined", "amount": 100})

        balance = json.loads((ROOT / "balance/progression_balance.json").read_text(encoding="utf-8"))
        economy = ResourceManager(new_game=True)
        buildings = BuildingManager(economy)
        mining = MiningManager(economy, initial_ship_count=0)
        fleet = SimpleNamespace(ships=[])
        technology = _Technology()
        galaxy = SimpleNamespace(systems={"sol": {"discovered": True}})
        colonies = SimpleNamespace(colonies=[])
        automation = SimpleNamespace(mining=mining, settings={})
        trade = SimpleNamespace(active=False, routes=[])
        campaign = CampaignManager(economy, buildings, mining, fleet, technology, galaxy, colonies, enabled=True)
        progression = GameProgression(economy, buildings, technology)
        game = SimpleNamespace(economy=economy, buildings=buildings, mining=mining,
            fleet=fleet, technology=technology, galaxy=galaxy, colony_manager=colonies,
            automation_manager=automation, trade_manager=trade, campaign_manager=campaign)

        # Normal one-time wreckage salvage and actual solar-array construction.
        ok, _ = progression.perform_salvage()
        self.assertTrue(ok)
        ok, _ = buildings.start_build("solar_array")
        self.assertTrue(ok)
        buildings.update(buildings.definition("solar_array")["build_time"])
        progression.update(game)
        self.assertEqual(progression.stage_id, "mining")
        self.assertTrue(mining.auto_dispatch_enabled)

        # Use solar production and the configured normal tutorial milestone reward.
        economy.update(12.0)
        for key, amount in balance["stage_rewards"]["power"]["resources"].items():
            economy.add(key, amount)
        campaign._recalculate()
        self.assertEqual(campaign.missions["mine"]["status"], "available")

        starting_metal = economy.get("metal").amount
        ok, message = mining.build_ship()
        self.assertTrue(ok, message)
        ship = mining.ships[0]
        self.assertEqual(ship.task, "outbound")
        campaign._recalculate()
        self.assertEqual(campaign.missions["mine"]["status"], "completed")
        self.assertEqual(campaign.missions["miner"]["status"], "available")

        # The real MiningManager performs flight, extraction, return and unloading.
        for _ in range(6):
            mining.update(30.0)
            if mining.delivered_total >= 100:
                break
        self.assertGreaterEqual(mining.delivered_total, 100.0)
        self.assertGreater(economy.get("metal").amount, starting_metal - MiningManager.SHIP_COST["metal"])
        campaign._recalculate()
        self.assertEqual(campaign.missions["miner"]["status"], "completed")
        progression.update(game)
        self.assertEqual(progression.stage_id, "station")


if __name__ == "__main__":
    unittest.main()
