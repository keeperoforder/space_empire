import json
import unittest
from pathlib import Path

from progression.balance_audit import audit_mandatory_cost_path, load_data, validate_graph
from progression.game_progression import GameProgression
from fleet.spaceship import SHIP_TYPES
from mining import MiningManager
from colonies.colony_manager import ColonyManager
from galaxy.galaxy_manager import GalaxyManager
from types import SimpleNamespace
from progression.game_progression import GameProgression


class ProgressionBalanceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.balance, self.costs, self.graph, self.buildings = load_data(self.root)

    def test_progression_graph_is_acyclic_and_all_edges_resolve(self):
        order = validate_graph(self.graph)
        self.assertEqual(len(order), len(self.graph["nodes"]))
        self.assertGreaterEqual(len(self.graph["edges"]), 20)

    def test_mandatory_resource_path_never_softlocks(self):
        result = audit_mandatory_cost_path(self.root)
        self.assertEqual(result["path"], "PASS")
        self.assertTrue(all(value >= 0 for value in result["remaining"].values()))

    def test_opening_balance_is_zero_and_salvage_only_funds_solar(self):
        self.assertTrue(all(v == 0 for v in self.balance["starting_state"]["resources"].values()))
        stock = dict(self.balance["salvage_reward"])
        for key, value in self.buildings["solar_array"]["cost"].items():
            stock[key] -= value
        self.assertTrue(all(value >= 0 for value in stock.values()))
        self.assertEqual(stock["metal"], 40)
        self.assertEqual(stock["science"], 0)

    def test_mining_and_colony_costs_are_externalized(self):
        self.assertEqual(MiningManager.SHIP_COST, self.costs["mining_ship"])
        self.assertEqual(ColonyManager.COLONIZE_COST, self.costs["colonization"])
        self.assertEqual(ColonyManager.BASE_COST, self.costs["colony_base"])
        for ship_type, cost in self.costs["ships"].items():
            self.assertEqual(SHIP_TYPES[ship_type]["cost"], cost)

    def test_galaxy_expedition_rewards_are_loaded_from_balance_config(self):
        self.assertEqual(GalaxyManager.REWARDS,
                         {key: tuple(value) for key, value in self.balance["expedition"]["rewards"].items()})

    def test_stage_reward_runtime_uses_progression_balance_file(self):
        economy = SimpleNamespace(get=lambda key: SimpleNamespace(free_capacity=999999))
        buildings = SimpleNamespace(count=lambda key: 0)
        technology = SimpleNamespace(set_research_enabled=lambda enabled: None)
        progression = GameProgression(economy, buildings, technology, data_dir=self.root / "progression")
        power = next(stage for stage in progression.stages if stage["id"] == "power")
        self.assertEqual(power["reward"], self.balance["stage_rewards"]["power"])

    def test_stage_rewards_are_loaded_from_balance_config(self):
        self.assertEqual(self.balance["stage_rewards"]["power"]["resources"]["fuel"], 55)
        self.assertEqual(self.balance["stage_rewards"]["station"]["resources"]["science"], 65)
        self.assertEqual(self.balance["stage_rewards"]["colonies"]["resources"]["metal"], 560)

    def test_two_colonies_are_mandatory_before_trade_unlock(self):
        campaign = json.loads((self.root / "progression" / "campaign_progression.json").read_text(encoding="utf-8"))
        automation = next(s for s in campaign["stages"] if s["id"] == "automation")
        empire = next(s for s in campaign["stages"] if s["id"] == "empire")
        self.assertEqual(automation["objective"]["type"], "automation_and_colonies")
        self.assertTrue(empire["objective"]["requires_two_colonies"])
        self.assertIn("second_colony", [edge[1] for edge in self.graph["edges"] if edge[0] == "automation"])

    def test_estimates_cover_all_ten_stages(self):
        self.assertEqual(len(self.balance["stage_estimates"]), 10)
        for estimate in self.balance["stage_estimates"].values():
            low, high = estimate["seconds"]
            self.assertGreaterEqual(low, 0)
            self.assertGreater(high, low)


if __name__ == "__main__":
    unittest.main()
