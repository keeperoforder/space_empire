"""Non-graphical regressions for HUD layout and scout objective accounting."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from campaign.campaign_manager import CampaignManager

ROOT = Path(__file__).resolve().parents[1]


class HudAndScoutRegressionTests(unittest.TestCase):
    def test_sidebar_layout_is_viewport_bounded_and_adaptive(self):
        source = (ROOT / "ui/sidebar.py").read_text(encoding="utf-8")
        self.assertIn("surface.get_rect()", source)
        self.assertIn("available_h // max(1, len(self.ITEMS))", source)
        self.assertIn("visible_count = max(1, min(len(self.ITEMS)", source)

    def test_developer_overlay_reserves_responsive_right_panel(self):
        source = (ROOT / "developer/dev_mode.py").read_text(encoding="utf-8")
        panel = (ROOT / "ui/right_panel.py").read_text(encoding="utf-8")
        self.assertIn("right_panel.width_for(w)", source)
        self.assertIn("available_width < 150", source)
        self.assertIn("def width_for(screen_width)", panel)

    def test_scout_objective_counts_only_registered_completed_ships(self):
        manager = CampaignManager.__new__(CampaignManager)
        manager.fleet = SimpleNamespace(ships=[])
        objective = {"type": "ship", "key": "scout", "amount": 1}
        self.assertEqual(manager._progress(objective), 0)
        manager.fleet.ships.append(SimpleNamespace(ship_type="scout"))
        self.assertEqual(manager._progress(objective), 1)
        manager.fleet.ships.append(SimpleNamespace(ship_type="fighter"))
        self.assertEqual(manager._progress(objective), 1)

    def test_ui_error_logger_preserves_full_exception_traceback(self):
        source = (ROOT / "ui/hud.py").read_text(encoding="utf-8")
        self.assertIn("traceback.format_exception(", source)
        self.assertIn("exc.__traceback__", source)
        self.assertIn("Space Empire UI error log failed", source)


if __name__ == "__main__":
    unittest.main()
