import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from economy import ResourceManager
from buildings import BuildingManager
from technology import TechnologyManager
from progression import GameProgression


class TutorialCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.economy = ResourceManager(new_game=True)
        self.buildings = BuildingManager(self.economy)
        self.tech = TechnologyManager(self.economy, save_path=Path(self.tmp.name) / "tech.json")
        self.progression = GameProgression(self.economy, self.buildings, self.tech)

    def tearDown(self):
        self.tmp.cleanup()

    def test_ten_stages_have_unique_ids_and_real_objectives(self):
        self.assertEqual(len(self.progression.stages), 10)
        ids = [stage["id"] for stage in self.progression.stages]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(stage.get("objective", {}).get("type") for stage in self.progression.stages))
        self.assertEqual(self.progression.current_task()["id"], "awakening")

    def test_salvage_advances_only_once_and_unlocks_power_stage(self):
        ok, _ = self.progression.perform_salvage()
        self.assertTrue(ok)
        self.assertEqual(self.progression.current_task()["id"], "power")
        self.assertTrue(self.progression.is_unlocked("building"))
        self.assertFalse(self.progression.is_unlocked("mining"))
        self.assertFalse(self.progression.perform_salvage()[0])

    def test_research_remains_locked_until_laboratory_is_built(self):
        self.progression.stage_index = 4
        self.progression.stage_id = "science"
        self.progression.active_task_id = "science"
        self.assertFalse(self.progression.is_unlocked("research"))
        self.assertFalse(self.tech.research_enabled)

    def test_only_current_stage_mechanics_are_unlocked(self):
        self.assertFalse(self.progression.is_unlocked("building"))
        for key in ("mining", "research", "fleet", "galaxy", "colonies", "automation", "trade"):
            self.assertFalse(self.progression.is_unlocked(key))
        self.progression.perform_salvage()
        self.assertTrue(self.progression.is_unlocked("building"))
        self.assertFalse(self.progression.is_unlocked("mining"))

    def test_stage_data_requires_two_colonies_before_trade_route(self):
        objective = self.progression.stages[9]["objective"]
        self.assertTrue(objective["requires_two_colonies"])
        self.assertEqual(objective["type"], "trade_route")

    def test_initial_sidebar_sections_are_exactly_overview_campaign_settings(self):
        expected = {"Огляд": "AVAILABLE", "Кампанія": "AVAILABLE",
                    "Налаштування": "AVAILABLE", "Будівництво": "LOCKED",
                    "Флот": "LOCKED", "Видобуток": "LOCKED",
                    "Дослідження": "LOCKED", "Планети": "LOCKED",
                    "Галактична карта": "LOCKED", "Торгівля": "LOCKED",
                    "Автоматизація": "LOCKED", "Оборона": "LOCKED"}
        for section, state in expected.items():
            self.assertEqual(self.progression.section_state(section)[0], state, section)

    def test_menu_unlocks_follow_real_buildings_ships_expeditions_and_technology(self):
        counts = {}
        game = SimpleNamespace(
            buildings=SimpleNamespace(count=lambda key: counts.get(key, 0)),
            fleet=SimpleNamespace(ships=[]),
            mining=SimpleNamespace(asteroids={"field_1": object()}, auto_dispatch_enabled=False),
            galaxy=SimpleNamespace(systems={"sol": {"discovered": True}}),
            colony_manager=SimpleNamespace(colonies={}),
            technology=SimpleNamespace(technologies={"ai_01": {"state": "locked"}},
                                       set_research_enabled=lambda enabled: None),
            campaign_manager=SimpleNamespace(active_event=None),
            automation_manager=SimpleNamespace(mining=SimpleNamespace(auto_dispatch_enabled=False)),
            trade_manager=SimpleNamespace(active=False),
        )
        self.progression.stage_index = 6
        self.progression.refresh_section_access(game)
        self.assertFalse(self.progression.is_unlocked("research"))
        self.assertFalse(self.progression.is_unlocked("fleet"))
        self.assertFalse(self.progression.is_unlocked("galaxy"))
        counts["laboratory"] = 1
        counts["hangar"] = 1
        game.fleet.ships = [SimpleNamespace(ship_type="scout"),
                            SimpleNamespace(ship_type="transport")]
        game.galaxy.systems["vega"] = {"discovered": True}
        self.progression.refresh_section_access(game)
        self.assertTrue(self.progression.is_unlocked("research"))
        self.assertTrue(self.progression.is_unlocked("fleet"))
        self.assertTrue(self.progression.is_unlocked("galaxy"))
        self.assertTrue(self.progression.is_unlocked("colonies"))
        game.colony_manager.colonies = {"planet_a": {}, "planet_b": {}}
        self.progression.refresh_section_access(game)
        self.assertTrue(self.progression.is_unlocked("trade"))
        self.assertFalse(self.progression.is_unlocked("automation"))
        game.technology.technologies["ai_01"]["state"] = "completed"
        self.progression.refresh_section_access(game)
        self.assertTrue(self.progression.is_unlocked("automation"))

    def test_defense_unlocks_only_on_danger_event(self):
        game = SimpleNamespace(
            buildings=SimpleNamespace(count=lambda key: 0),
            fleet=SimpleNamespace(ships=[]),
            mining=SimpleNamespace(asteroids={}, auto_dispatch_enabled=False),
            galaxy=SimpleNamespace(systems={}),
            colony_manager=SimpleNamespace(colonies={}),
            technology=SimpleNamespace(technologies={}, set_research_enabled=lambda enabled: None),
            campaign_manager=SimpleNamespace(active_event={"category": "Сюжет"}),
            automation_manager=SimpleNamespace(mining=SimpleNamespace(auto_dispatch_enabled=False)),
            trade_manager=SimpleNamespace(active=False),
        )
        self.progression.refresh_section_access(game)
        self.assertFalse(self.progression.is_unlocked("defense"))
        game.campaign_manager.active_event = {"category": "Небезпека"}
        self.progression.refresh_section_access(game)
        self.assertTrue(self.progression.is_unlocked("defense"))

    def test_legacy_unlock_flags_are_not_trusted(self):
        self.progression.restore({
            "version": 2, "stage_index": 8, "stage_id": "automation",
            "active_task_id": "automation", "unlocks": {
                key: True for key in self.progression.MECHANIC_LABELS
            }
        })
        self.assertFalse(self.progression.is_unlocked("automation"))
        self.assertFalse(self.progression.is_unlocked("fleet"))
        self.assertTrue(self.progression.is_unlocked("campaign"))

    def test_snapshot_restores_single_active_stage_and_unlocks(self):
        self.progression.perform_salvage()
        state = self.progression.snapshot()
        other = GameProgression(self.economy, self.buildings, self.tech)
        other.restore(state)
        self.assertEqual(other.stage_id, "power")
        self.assertTrue(other.salvage_used)
        self.assertEqual(sum(1 for s in other.stages if s["id"] == other.current_task()["id"]), 1)

    def test_previous_two_stage_save_migrates_to_power_stage(self):
        self.progression.restore({
            "version": 1, "stage_id": "first_power", "active_task_id": "restore_power",
            "commander_level": 1, "commander_xp": 25,
            "completed_tasks": ["collect_wreckage"],
            "claimed_rewards": ["initial_wreckage_salvage"],
            "salvage_used": True, "unlocks": {"building": True}
        })
        self.assertEqual(self.progression.stage_id, "power")
        self.assertEqual(self.progression.active_task_id, "power")
        self.assertTrue(self.progression.salvage_used)
        self.assertIn("awakening", self.progression.completed_tasks)

    def test_stage_rewards_are_idempotent(self):
        stage = self.progression.stages[1]
        before = self.economy.get("metal").amount
        self.progression._grant_stage_reward(stage)
        once = self.economy.get("metal").amount
        self.progression._grant_stage_reward(stage)
        self.assertGreater(once, before)
        self.assertEqual(self.economy.get("metal").amount, once)


if __name__ == "__main__":
    unittest.main()
