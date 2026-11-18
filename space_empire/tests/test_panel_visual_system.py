import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = (
    "build_panel.py", "research_panel.py", "campaign_panel.py", "progression_panel.py",
    "fleet_panel.py", "colony_panel.py", "galaxy_panel.py", "settings_panel.py",
    "trade_panel.py", "automation_panel.py", "mining_panel.py",
)


class PanelVisualSystemTests(unittest.TestCase):
    def test_shared_theme_exposes_unified_components(self):
        tree = ast.parse((ROOT / "ui/theme.py").read_text(encoding="utf-8"))
        names = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue({"panel", "section_header", "action_button", "info_card", "label"} <= names)

    def test_all_management_panels_use_shared_theme(self):
        for name in PANELS:
            path = ROOT / "ui" / name
            if path.exists():
                source = path.read_text(encoding="utf-8")
                self.assertIn("theme", source, name)

    def test_building_actions_keep_same_hit_rects_and_labels(self):
        source = (ROOT / "ui/build_panel.py").read_text(encoding="utf-8")
        for token in ("self.build_rect", "self.upgrade_rect", "ПОБУДУВАТИ", "ПОКРАЩИТИ",
                      'build_time', 'energy_consumption',
                      "definition.get"):
            self.assertIn(token, source)

    def test_window_event_apis_remain(self):
        for name in PANELS:
            path = ROOT / "ui" / name
            if not path.exists():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
            for cls in classes:
                methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
                if "draw" in methods:
                    self.assertIn("handle_event", methods, name)


if __name__ == "__main__":
    unittest.main()
