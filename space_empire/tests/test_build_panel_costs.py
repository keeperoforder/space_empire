import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildPanelCostFormatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / "ui" / "build_panel.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        panel = next(node for node in tree.body
                     if isinstance(node, ast.ClassDef) and node.name == "BuildPanel")
        method = next(node for node in panel.body
                      if isinstance(node, ast.FunctionDef) and node.name == "_cost_text")
        module = ast.Module(body=[method], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {}
        exec(compile(module, "build_panel_cost_formatter", "exec"), namespace)
        cls.format_cost = staticmethod(namespace["_cost_text"])

    def test_solar_array_cost_is_renderable(self):
        rendered = self.format_cost({
            "metal": 90, "energy": 20, "crystals": 8,
            "fuel": 5, "credits": 35
        })
        self.assertEqual(rendered, "МЕТ 90 • ЕН 20 • КР 8 • ПАЛ 5 • КРЕД 35")

    def test_empty_cost_is_explicit(self):
        self.assertEqual(self.format_cost({}), "Безкоштовно")

    def test_unknown_resource_is_not_dropped(self):
        self.assertEqual(self.format_cost({"rare_alloy": 2}), "RARE_ALLOY 2")


if __name__ == "__main__":
    unittest.main()
