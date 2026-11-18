import ast
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ReleasePackageTests(unittest.TestCase):
    def test_all_json_data_files_parse(self):
        files=list(ROOT.rglob("*.json"))
        self.assertGreaterEqual(len(files),7)
        for path in files:
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_game_supports_new_and_continue_modes(self):
        tree=ast.parse((ROOT/"game.py").read_text(encoding="utf-8"))
        game=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Game")
        init=next(n for n in game.body if isinstance(n,ast.FunctionDef) and n.name=="__init__")
        self.assertIn("load_saved",[a.arg for a in init.args.args])

    def test_settings_are_connected_to_hud(self):
        hud=(ROOT/"ui"/"hud.py").read_text(encoding="utf-8")
        self.assertIn("SettingsPanel(game, self.bottom)",hud)
        self.assertIn('(self.settings_panel, "Налаштування")',hud)

    def test_release_assets_and_build_files_exist(self):
        required=[
            "requirements.txt","README.md","launcher.py","SpaceEmpire.spec",
            "build_windows.bat","assets/icons/space_empire.ico",
            "assets/icons/space_empire.png","assets/audio/ambient_loop.wav",
            "assets/audio/ui_click.wav","ui/settings_panel.py"
        ]
        for rel in required:
            with self.subTest(file=rel): self.assertTrue((ROOT/rel).is_file())

    def test_launcher_does_not_shadow_global_config(self):
        tree=ast.parse((ROOT/"launcher.py").read_text(encoding="utf-8"))
        launcher=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="run_launcher")
        local_config_imports=[
            n for n in ast.walk(launcher)
            if isinstance(n,ast.Import) and any(alias.name=="config" for alias in n.names)
        ]
        self.assertEqual(local_config_imports, [])

    def test_launcher_has_all_required_screens(self):
        text=(ROOT/"launcher.py").read_text(encoding="utf-8")
        for state in ('"splash"','"menu"','"settings"','"loading"'):
            self.assertIn(state,text)


    def test_continue_button_is_conditional_on_valid_save(self):
        launcher = (ROOT / "launcher.py").read_text(encoding="utf-8")
        self.assertIn("def has_continue_save()", launcher)
        self.assertIn("if continue_available:", launcher)
        self.assertIn('labels.append(("continue","Продовжити"))', launcher)

    def test_new_game_requires_confirmation_and_archives_previous_saves(self):
        launcher = (ROOT / "launcher.py").read_text(encoding="utf-8")
        game = (ROOT / "game.py").read_text(encoding="utf-8")
        self.assertIn('state="confirm_new"', launcher)
        self.assertIn('"confirm_yes"', launcher)
        self.assertIn('"confirm_no"', launcher)
        self.assertIn("archive_existing_files", game)
        self.assertNotIn("save_file.unlink", game)


    def test_hud_isolates_panel_event_and_render_failures(self):
        source = (ROOT / "ui" / "hud.py").read_text(encoding="utf-8")
        self.assertIn("def _safe_panel_event", source)
        self.assertIn("def _safe_panel_draw", source)
        self.assertIn("ui_errors.log", source)

    def test_build_panel_handles_empty_or_invalid_unlocked_catalog(self):
        source = (ROOT / "ui" / "build_panel.py").read_text(encoding="utf-8")
        self.assertIn("if not allowed_definitions:", source)
        self.assertIn("if self.selected_id not in allowed_ids:", source)

    def test_campaign_panel_handles_missing_chapter_data(self):
        source = (ROOT / "ui" / "campaign_panel.py").read_text(encoding="utf-8")
        self.assertIn("if not ch:", source)
        manager = (ROOT / "campaign" / "campaign_manager.py").read_text(encoding="utf-8")
        self.assertIn("if not self.chapters:", manager)

    def test_all_sidebar_sections_have_progression_rules(self):
        sidebar = (ROOT / "ui" / "sidebar.py").read_text(encoding="utf-8")
        progression = (ROOT / "progression" / "game_progression.py").read_text(encoding="utf-8")
        names = re.findall(r'\("[^"]+", "([^"]+)"\)', sidebar.split("def __init__", 1)[0])
        rules_text = progression.split("SECTION_REQUIREMENTS =", 1)[1].split("SECTION_COMPLETION =", 1)[0]
        rules = set(re.findall(r'"([^"]+)": \(', rules_text))
        for name in names:
            self.assertIn(name, rules, name)


    def test_campaign_panel_uses_tutorial_progression_and_build_action(self):
        source = (ROOT / "ui" / "campaign_panel.py").read_text(encoding="utf-8")
        self.assertIn("self.progression.current_task()", source)
        self.assertIn("Відновити енергосистему станції", source)
        self.assertIn("ПЕРЕЙТИ ДО БУДІВНИЦТВА", source)
        self.assertIn("self.on_build()", source)

    def test_new_game_runs_one_time_salvage_prologue_before_saving(self):
        source = (ROOT / "game.py").read_text(encoding="utf-8")
        self.assertIn("self.progression.perform_salvage()", source)
        self.assertIn("self.safe_save()", source)
        self.assertLess(source.index("self.progression.perform_salvage()"),
                        source.index("self.safe_save()", source.index("self.progression.perform_salvage()")))

    def test_building_panel_exposes_solar_cost_and_real_build_action(self):
        source = (ROOT / "ui" / "build_panel.py").read_text(encoding="utf-8")
        self.assertIn('self.manager.start_build(self.selected_id)', source)
        self.assertIn('self._cost_text(cost)', source)
        catalog = json.loads((ROOT / "buildings" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["solar_array"]["production"]["energy"], 8.0)


    def test_panel_guard_does_not_hide_panels_after_draw_or_event_errors(self):
        guard = (ROOT / "ui" / "panel_guard.py").read_text(encoding="utf-8")
        self.assertIn("Crucially, do not set panel.visible=False here.", guard)
        self.assertIn("return True", guard)
        hud = (ROOT / "ui" / "hud.py").read_text(encoding="utf-8")
        self.assertIn("self.panel_guard.draw(panel, surface, component)", hud)
        self.assertNotIn("panel.visible = False", hud.replace("self.progression_panel.visible = False", ""))


    def test_hud_imports_panel_guard_before_instantiation(self):
        source = (ROOT / "ui" / "hud.py").read_text(encoding="utf-8")
        self.assertIn("from ui.panel_guard import PanelGuard", source)
        self.assertLess(source.index("from ui.panel_guard import PanelGuard"),
                        source.index("self.panel_guard = PanelGuard("))

if __name__=="__main__": unittest.main()
