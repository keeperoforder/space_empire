"""Real fleet-production path and structural audit of all campaign missions."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from fleet import FleetManager, SHIP_TYPES
from campaign import CampaignManager

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
        self.assertIn("self.collapsed = True", source)
        self.assertIn("pygame.MOUSEWHEEL", source)
        self.assertIn("panel_height = 48 if self.collapsed else min(340 if self.compact else 560, h - 100)", source)
        self.assertIn('summary = (f"AUTO {tester.state}', source)
        self.assertIn("pygame.K_F11", source)
        self.assertIn("pygame.K_F12", source)
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
