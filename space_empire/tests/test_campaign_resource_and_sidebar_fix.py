import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CampaignFuelAndSidebarFixTests(unittest.TestCase):
    def test_mining_reward_funds_smelter_and_warehouse_after_miner_trip(self):
        balance = json.loads((ROOT / "balance/progression_balance.json").read_text(encoding="utf-8"))
        buildings = json.loads((ROOT / "buildings/catalog.json").read_text(encoding="utf-8"))
        salvage_fuel = balance["salvage_reward"]["fuel"]
        solar_fuel = buildings["solar_array"]["cost"]["fuel"]
        miner_fuel = json.loads((ROOT / "balance/economy_costs.json").read_text(encoding="utf-8"))["mining_ship"]["fuel"]
        trip_fuel = balance["critical_reserves"]["miner_round_trip_fuel"]
        power_reward = balance["stage_rewards"]["power"]["resources"]["fuel"]
        mining_reward = balance["stage_rewards"]["mining"]["resources"]["fuel"]
        mandatory_build_fuel = buildings["smelter"]["cost"]["fuel"] + buildings["warehouse"]["cost"]["fuel"]
        available_before_station = salvage_fuel - solar_fuel + power_reward - miner_fuel - trip_fuel + mining_reward
        self.assertGreaterEqual(available_before_station, mandatory_build_fuel)
        self.assertGreaterEqual(available_before_station - mandatory_build_fuel, 0)
        self.assertEqual(mining_reward, 60)

    def test_campaign_requires_mining_ship_before_mining_delivery(self):
        campaign = json.loads((ROOT / "campaign/campaign.json").read_text(encoding="utf-8"))
        missions = {mission["id"]: mission for mission in campaign["missions"]}
        self.assertEqual(missions["mine"]["objective"], {"type": "mining_ship", "amount": 1})
        self.assertEqual(missions["miner"]["objective"]["type"], "mined")
        chapter = next(item for item in campaign["chapters"] if item["id"] == "first_resources")
        self.assertEqual(chapter["missions"], ["mine", "miner"])
    def test_fuel_plant_is_not_required_before_station_stage(self):
        balance = json.loads((ROOT / "balance/progression_balance.json").read_text(encoding="utf-8"))
        self.assertNotIn("fuel_plant", balance["available_buildings_by_stage"]["station"])
        self.assertIn("fuel_plant", balance["available_buildings_by_stage"]["galaxy"])

    def test_sidebar_has_thirteen_distinct_semantic_vector_icons_and_larger_labels(self):
        source = (ROOT / "ui/sidebar.py").read_text(encoding="utf-8")
        self.assertIn("WIDTH = 220", source)
        self.assertIn("15,label_color", source)
        self.assertIn("def _draw_icon", source)
        for icon in ("overview", "build", "fleet", "mining", "research", "planets",
                     "galaxy", "trade", "automation", "campaign", "progress",
                     "defense", "settings"):
            self.assertIn(f'kind == "{icon}"', source)

    def test_global_theme_improves_minimum_font_size_and_muted_contrast(self):
        source = (ROOT / "ui/theme.py").read_text(encoding="utf-8")
        self.assertIn("max(10, int(size))", source)
        self.assertIn("MUTED = (158, 184, 205)", source)


if __name__ == "__main__":
    unittest.main()
