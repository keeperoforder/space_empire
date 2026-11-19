"""Real fleet-production path and structural audit of all campaign missions."""
import json
import unittest
import pygame
from pathlib import Path
from types import SimpleNamespace

from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from fleet import FleetManager, SHIP_TYPES
from campaign import CampaignManager
from developer.dev_mode import DeveloperMode, SPEEDS
from developer.automated_tester import AutomatedCampaignTester

ROOT = Path(__file__).resolve().parents[1]


class ScoutMissionFlowTests(unittest.TestCase):
    def setUp(self):
        self.resources = ResourceManager()
        self.buildings = BuildingManager(self.resources)
        self.mining = MiningManager(self.resources, initial_ship_count=0)
        self.fleet = FleetManager(self.resources, self.buildings, self.mining)
        self.technology = SimpleNamespace(technologies={})
        self.galaxy = SimpleNamespace(systems={})
        self.colonies = SimpleNamespace(colonies=[])
        self.campaign = CampaignManager(
            self.resources, self.buildings, self.mining, self.fleet,
            self.technology, self.galaxy, self.colonies
        )
        for mission_id in ("power", "metal", "mine", "miner"):
            self.campaign.missions[mission_id]["status"] = "completed"
        self.campaign._recalculate()

    def test_scout_requires_hangar_and_registers_after_real_construction(self):
        mission = self.campaign.missions["scout"]
        self.assertEqual(mission["status"], "available")
        self.assertEqual(mission["objective"],
                         {"type": "ship", "key": "scout", "amount": 1})
        ok, message = self.fleet.build_ship("scout")
        self.assertFalse(ok)
        self.assertIn("ангар", message.lower())
        self.assertEqual(self.campaign._progress(mission["objective"]), 0)

        ok, message = self.buildings.start_build("hangar")
        self.assertTrue(ok, message)
        self.buildings.update(self.buildings.definition("hangar")["build_time"])
        self.assertEqual(self.buildings.count("hangar"), 1)

        before = {key: self.resources.get(key).amount for key in SHIP_TYPES["scout"]["cost"]}
        ok, message = self.fleet.build_ship("scout")
        self.assertTrue(ok, message)
        self.assertTrue(any(self.resources.get(key).amount < before[key] for key in before))
        self.assertEqual(self.campaign._progress(mission["objective"]), 0)
        duration = next(p["duration"] for p in self.fleet.constructions
                        if p["ship_type"] == "scout")
        self.fleet.update(duration - 0.01)
        self.assertEqual(self.campaign._progress(mission["objective"]), 0)
        self.fleet.update(0.02)
        self.assertEqual(len([ship for ship in self.fleet.ships
                              if ship.ship_type == "scout"]), 1)
        self.campaign._recalculate()
        self.assertEqual(self.campaign._progress(mission["objective"]), 1)
        self.assertEqual(mission["status"], "completed")

    def test_unpaid_upkeep_does_not_interrupt_active_scout_expedition(self):
        ok, message = self.buildings.start_build("hangar")
        self.assertTrue(ok, message)
        self.buildings.update(self.buildings.definition("hangar")["build_time"])
        ok, message = self.fleet.build_ship("scout")
        self.assertTrue(ok, message)
        duration = next(p["duration"] for p in self.fleet.constructions
                        if p["ship_type"] == "scout")
        self.fleet.update(duration)
        scout = next(ship for ship in self.fleet.ships if ship.ship_type == "scout")

        credits = self.resources.get("credits")
        credits.amount = 0.0
        scout.task, scout.status = "explore", "outbound"
        original_hull = scout.hull
        self.fleet._maintenance(1.0)

        self.assertEqual(scout.task, "explore")
        self.assertEqual(scout.status, "outbound")
        self.assertEqual(scout.hull, original_hull)
        self.assertGreater(scout.maintenance_due, 0.0)

        scout.task, scout.status = "idle", "ready"
        credits.amount = 10.0
        self.fleet._maintenance(1.0)
        self.assertEqual(scout.maintenance_due, 0.0)



class AutomatedTesterScoutAvailabilityTests(unittest.TestCase):
    def _make_tester(self, construction=False):
        scout = SimpleNamespace(ship_type="scout", status="maintenance", task="idle")
        fleet = SimpleNamespace(
            ships=[scout],
            constructions=([{"ship_type": "scout"}] if construction else []),
        )
        fleet.build_calls = []
        def build_ship(ship_type):
            fleet.build_calls.append(ship_type)
            return True, "queued"
        fleet.build_ship = build_ship
        buildings = SimpleNamespace(count=lambda key: 1)
        galaxy = SimpleNamespace(
            systems={"sol": {"discovered": True},
                     "vega": {"discovered": False, "accessible": True}},
            expeditions={},
            available_scouts=lambda current_fleet: [],
            launch_expedition=lambda *args: self.fail("Unavailable scout must not launch"),
        )
        campaign = SimpleNamespace(_progress=lambda objective: 1)
        game = SimpleNamespace(fleet=fleet, buildings=buildings, galaxy=galaxy,
                               campaign_manager=campaign)
        tester = AutomatedCampaignTester.__new__(AutomatedCampaignTester)
        tester.game = game
        tester.current_step = ""
        tester.elapsed_without_progress = 0
        tester._fail = lambda *args, **kwargs: self.fail("Unexpected tester failure")
        return tester, fleet

    def test_unavailable_owned_scout_triggers_legitimate_replacement_build(self):
        tester, fleet = self._make_tester()
        tester._execute({"id": "systems", "title": "Nearby Star",
                         "objective": {"type": "systems", "amount": 2}})
        self.assertEqual(fleet.build_calls, ["scout"])
        self.assertIn("FleetManager", tester.current_step)

    def test_existing_scout_construction_is_not_duplicated(self):
        tester, fleet = self._make_tester(construction=True)
        tester._execute({"id": "systems", "title": "Nearby Star",
                         "objective": {"type": "systems", "amount": 2}})
        self.assertEqual(fleet.build_calls, [])
        self.assertIn("Wait for scout construction", tester.current_step)

    def test_maintenance_scout_waits_instead_of_building_a_duplicate(self):
        tester, fleet = self._make_tester()
        credits = SimpleNamespace(amount=100, balance=3.0)
        tester.game.economy = SimpleNamespace(get=lambda key: credits)
        tester._execute({"id": "systems", "title": "Nearby Star",
                         "objective": {"type": "systems", "amount": 2}})
        self.assertEqual(fleet.build_calls, [])
        self.assertIn("maintenance recovery", tester.current_step)


class _FakeAutomatedTester:
    def __init__(self):
        self.state = "RUNNING"

    def pause(self):
        if self.state == "RUNNING":
            self.state = "PAUSED"

    def resume(self):
        if self.state == "PAUSED":
            self.state = "RUNNING"

    def stop(self):
        if self.state in ("RUNNING", "PAUSED"):
            self.state = "STOPPED"


class DeveloperModeSpeedControlTests(unittest.TestCase):
    def setUp(self):
        self.tools = DeveloperMode.__new__(DeveloperMode)
        self.tools.speed_index = 0
        self.tools.status = ""
        self.tools.messages = []
        self.tools.paused = False
        self.tools.automated_tester = _FakeAutomatedTester()
        self.tools.visible = True
        self.tools.buttons = {}
        self.tools._content_rect = pygame.Rect(100, 100, 1, 1)

    def test_every_supported_speed_can_be_selected(self):
        self.assertEqual(SPEEDS, (1, 2, 5, 10, 50, 100))
        for factor in SPEEDS:
            with self.subTest(speed=factor):
                self.assertTrue(self.tools.set_test_speed(factor))
                self.assertEqual(self.tools.speed, factor)
                self.assertIn(f"{factor}x", self.tools.status)
        self.assertFalse(self.tools.set_test_speed(3))
        self.assertEqual(self.tools.speed, 100)

    def test_speed_button_click_changes_selected_simulation_speed(self):
        self.tools.buttons = {"speed_50": pygame.Rect(10, 10, 40, 22)}
        event = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(15, 15))
        self.assertTrue(self.tools.handle_event(event))
        self.assertEqual(self.tools.speed, 50)

    def test_pause_resume_and_stop_update_tester_state(self):
        self.tools.pause_automated_test()
        self.assertEqual(self.tools.automated_tester.state, "PAUSED")
        self.assertTrue(self.tools.paused)

        self.tools.resume_automated_test()
        self.assertEqual(self.tools.automated_tester.state, "RUNNING")
        self.assertFalse(self.tools.paused)

        self.tools.stop_automated_test()
        self.assertEqual(self.tools.automated_tester.state, "STOPPED")
        self.assertFalse(self.tools.paused)

    def test_speed_controls_are_rendered_outside_scroll_area(self):
        source = (ROOT / "developer" / "dev_mode.py").read_text(encoding="utf-8")
        self.assertIn('txt(f"TEST SPEED: {self.speed}x', source)
        self.assertIn("for i, factor in enumerate(SPEEDS)", source)
        self.assertIn('key.startswith("speed_")', source)
        self.assertIn("self.set_test_speed(factor)", source)
        game_source = (ROOT / "game.py").read_text(encoding="utf-8")
        self.assertIn("dt *= self.dev_tools.speed", game_source)


class CampaignAuditStructureTests(unittest.TestCase):
    def test_campaign_has_sixteen_unique_missions_linked_to_eight_chapters(self):
        data = json.loads((ROOT / "campaign" / "campaign.json").read_text(encoding="utf-8"))
        ids = [mission["id"] for mission in data["missions"]]
        linked = [mid for chapter in data["chapters"] for mid in chapter["missions"]]
        self.assertEqual(len(data["chapters"]), 8)
        self.assertEqual(len(ids), 16)
        self.assertEqual(len(set(ids)), 16)
        self.assertEqual(len(linked), 16)
        self.assertEqual(set(linked), set(ids))

    def test_all_sixteen_missions_use_supported_objective_types(self):
        data = json.loads((ROOT / "campaign" / "campaign.json").read_text(encoding="utf-8"))
        supported = {"resource", "building", "mined", "mining_ship", "ship",
                     "fleet", "systems", "colonies", "colony_level", "flag",
                     "tech_count", "tech_keyword"}
        for mission in data["missions"]:
            self.assertIn(mission["objective"]["type"], supported, mission["id"])

    def test_developer_panel_is_compact_collapsible_and_scrollable(self):
        source = (ROOT / "developer" / "dev_mode.py").read_text(encoding="utf-8")
        self.assertIn("self.compact = True", source)
        self.assertIn("self.collapsed = False", source)
        self.assertIn("pygame.MOUSEWHEEL", source)
        self.assertIn("panel_height = min(340 if self.compact else 560", source)
        self.assertIn('"toggle_compact": lambda', source)

    def test_navigation_and_topbar_imports_are_present(self):
        sidebar = (ROOT / "ui" / "sidebar.py").read_text(encoding="utf-8")
        topbar = (ROOT / "ui" / "top_bar.py").read_text(encoding="utf-8")
        theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
        self.assertIn("import math", sidebar)
        self.assertIn("from ui import theme", topbar)
        self.assertIn("def resource_glyph(", theme)


if __name__ == "__main__":
    unittest.main()
