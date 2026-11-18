import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def class_methods(relative_path, class_name):
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.name for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


class UIVisualUpgradeRegressionTests(unittest.TestCase):
    def test_top_bar_keeps_resource_event_and_draw_api(self):
        methods = class_methods("ui/top_bar.py", "TopBar")
        self.assertTrue({"handle_event", "draw", "tooltip_text"} <= methods)

    def test_sidebar_keeps_navigation_and_hover_api(self):
        methods = class_methods("ui/sidebar.py", "Sidebar")
        self.assertTrue({"handle_event", "draw", "update"} <= methods)

    def test_right_and_bottom_panels_keep_draw_api(self):
        self.assertIn("draw", class_methods("ui/right_panel.py", "RightPanel"))
        self.assertIn("draw", class_methods("ui/bottom_bar.py", "BottomBar"))

    def test_resource_glyphs_cover_all_six_resource_types(self):
        source = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
        for resource in ("metal", "energy", "crystals", "fuel", "credits", "science"):
            self.assertIn(f'kind == "{resource}"', source)

    def test_build_panel_and_hud_navigation_routes_remain(self):
        build_methods = class_methods("ui/build_panel.py", "BuildPanel")
        hud_methods = class_methods("ui/hud.py", "HUD")
        self.assertTrue({"open", "close", "handle_event", "draw"} <= build_methods)
        self.assertTrue({"handle_event", "draw", "update"} <= hud_methods)

    def test_station_core_sprite_factory_remains(self):
        source = (ROOT / "graphics" / "station_sprites.py").read_text(encoding="utf-8")
        self.assertIn("def make_core():", source)
        self.assertIn("Extra pixel-art surface detail", source)


if __name__ == "__main__":
    unittest.main()
