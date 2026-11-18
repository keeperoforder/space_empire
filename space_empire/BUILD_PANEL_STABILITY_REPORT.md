# Space Empire — виправлення стабільності конструктора

## Першопричина

У `ui/hud.py` метод `_safe_panel_draw()` перехоплював будь-який виняток під час промальовування панелі та виконував `panel.visible = False`. Тобто навіть короткочасна помилка рендерингу автоматично закривала конструктор. Аналогічний ризик був в обробці подій: `_safe_panel_event()` також приховував панель після винятку. Це і є точний механізм самовільного закриття, який підтверджено кодом.

Визначити конкретний виняток усередині графічного рендерингу, який запускав цей механізм у користувача, не вдалося: Pygame у середовищі відсутній, мережа недоступна, тому запустити оригінальний GUI та отримати runtime traceback неможливо.

## Виправлення

- Додано `ui/panel_guard.py` — ізольований обробник подій/рендерингу, який зберігає `visible`, вибрану споруду та стан панелі навіть при винятку.
- `ui/hud.py` більше не закриває панель при помилці малювання чи обробки події. Помилка логуються через наявний `saves/ui_errors.log`; однакова помилка не засмічує лог щокадру.
- Якщо рендеринг панелі падає, HUD показує діагностичне повідомлення на місці панелі, але не скидає розділ і не ховає конструктор.
- У штатному сценарії конструктор закривається лише явним натисканням хрестика або переходом в інший розділ.
- Логіка каталогу, вибору сонячної панелі, вартості, списання ресурсів, завершення будівництва та виробництва енергії не переписувалася.

## Перевірки

- Автоматичні тести: 129/129 PASS.
- Python AST: 79/79 файлів PASS.
- JSON: 13/13 файлів PASS.
- `compileall`: PASS.
- Новий 30-секундний регресійний тест: 1 800 послідовних спроб малювання з примусово згенерованою помилкою; панель залишилася видимою на кожному кроці; однаковий traceback записувався один раз.
- Новий тест помилки події: виняток поглинається, панель залишається видимою, `selected_id='solar_array'` не скидається.
- Існуючі тести будівництва перевіряють списання ресурсів, завершення сонячної панелі та +8 енергії/с.

## Обмеження

Не виконано реальний запуск нової гри, GUI-кліки, очікування 30 секунд у Pygame-вікні та фізичне відображення спрайта станції. Pygame відсутній, а встановити його з PyPI неможливо через недоступність мережі. 30-секундна перевірка виконана як автоматизований тест 1 800 циклів рендерингу через той самий новий механізм PanelGuard, а не як реальний графічний runtime.

## Повний код змінених файлів

### `ui/hud.py`
```python
"""HUD composition, input routing and adaptive layout."""
import pygame
import traceback
from pathlib import Path
from ui.top_bar import TopBar
from ui.sidebar import Sidebar
from ui.right_panel import RightPanel
from ui.bottom_bar import BottomBar
from ui.tooltip import Tooltip
from ui.build_panel import BuildPanel
from ui.mining_panel import MiningPanel
from ui.fleet_panel import FleetPanel
from ui.research_panel import ResearchPanel
from ui.offline_report import OfflineReport
from ui.galaxy_panel import GalaxyPanel
from ui.colony_panel import ColonyPanel
from ui.automation_panel import AutomationPanel
from ui.trade_panel import TradePanel
from ui.campaign_panel import CampaignPanel
from ui.settings_panel import SettingsPanel
from ui.progression_panel import ProgressionPanel


class HUD:
    def __init__(self, resource_manager, building_manager, station, mining_manager, fleet_manager=None, technology_manager=None, offline_report=None, galaxy_manager=None, colony_manager=None, automation_manager=None, trade_manager=None, campaign_manager=None, game=None, progression=None):
        self.top = TopBar(resource_manager, progression)
        self.sidebar = Sidebar(progression, None)
        self.right = RightPanel()
        self.bottom = BottomBar()
        self.tooltip = Tooltip()
        self.panel_guard = PanelGuard(self._report_ui_error)
        self.current_section = "Огляд"
        self.build_panel = BuildPanel(building_manager, resource_manager, self.bottom, progression)
        self.station = station
        self.mining_panel = MiningPanel(mining_manager, self.bottom)
        self.fleet_panel = FleetPanel(fleet_manager, self.bottom) if fleet_manager else None
        self.research_panel = ResearchPanel(technology_manager, self.bottom) if technology_manager else None
        self.offline_report = OfflineReport(offline_report) if offline_report else None
        self.galaxy_panel = GalaxyPanel(galaxy_manager, fleet_manager, self.bottom) if galaxy_manager and fleet_manager else None
        self.colony_panel = ColonyPanel(colony_manager, fleet_manager, self.bottom) if colony_manager and fleet_manager else None
        self.automation_panel = AutomationPanel(automation_manager, self.bottom) if automation_manager else None
        self.trade_panel = TradePanel(trade_manager, colony_manager, fleet_manager, self.bottom) if trade_manager and colony_manager and fleet_manager else None
        self.campaign_panel = CampaignPanel(
            campaign_manager, self.bottom, progression,
            on_build=self._open_build_from_campaign
        ) if campaign_manager else None
        self.settings_panel = SettingsPanel(game, self.bottom) if game else None
        self.progression_panel = ProgressionPanel(progression, self.bottom) if progression else None
        self.sidebar.event_log = self.bottom
        if self.progression_panel and progression.intro_seen:
            self.progression_panel.visible = False

    def _open_build_from_campaign(self):
        self.current_section = "Будівництво"
        self.sidebar.active = "Будівництво"
        self.right.set_section("Будівництво")
        self.build_panel.open()
        self.campaign_panel.close()
        self.mining_panel.close()
        if self.fleet_panel:
            self.fleet_panel.close()
        if self.research_panel:
            self.research_panel.close()

    def _report_ui_error(self, component, exc):
        message = f"Помилка інтерфейсу ({component}): {type(exc).__name__}: {exc}"
        try:
            self.bottom.push(message)
        except Exception:
            pass
        try:
            log_path = Path(__file__).resolve().parent.parent / "saves" / "ui_errors.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write("\\n" + message + "\\n")
                stream.write(traceback.format_exc())
                stream.write("\\n")
        except OSError:
            pass

    def _safe_panel_event(self, panel, event, component):
        return self.panel_guard.handle_event(panel, event, component)

    def _safe_panel_draw(self, panel, surface, component):
        ok = self.panel_guard.draw(panel, surface, component)
        if not ok and panel is not None and getattr(panel, "visible", False):
            # Keep the panel open and make the rendering fault visible without
            # changing the current section or discarding the selected building.
            try:
                rect = getattr(panel, "panel_rect", pygame.Rect(220, 86, 430, 150))
                if not isinstance(rect, pygame.Rect) or rect.width <= 0 or rect.height <= 0:
                    rect = pygame.Rect(220, 86, 430, 150)
                rect = rect.clip(surface.get_rect())
                if rect.width > 0 and rect.height > 0:
                    pygame.draw.rect(surface, (70, 24, 30), rect, border_radius=7)
                    pygame.draw.rect(surface, (220, 90, 90), rect, 2, border_radius=7)
                    theme_message = "ПОМИЛКА ВІДОБРАЖЕННЯ — ПАНЕЛЬ ЗАЛИШАЄТЬСЯ ВІДКРИТОЮ"
                    font = pygame.font.SysFont("segoeui", 12)
                    surface.blit(font.render(theme_message, True, (255, 190, 190)),
                                 (rect.x + 12, rect.y + 12))
            except Exception:
                pass

    def handle_event(self, event):
        event_panels = (
            (self.progression_panel, "Прогрес"),
            (self.settings_panel, "Налаштування"),
            (self.campaign_panel, "Кампанія"),
            (self.automation_panel, "Автоматизація"),
            (self.trade_panel, "Торгівля"),
            (self.colony_panel, "Планети"),
            (self.galaxy_panel, "Галактична карта"),
            (self.offline_report, "Офлайн-звіт"),
            (self.build_panel, "Будівництво"),
            (self.mining_panel, "Видобуток"),
            (self.fleet_panel, "Флот"),
            (self.research_panel, "Дослідження"),
        )
        for panel, name in event_panels:
            if self._safe_panel_event(panel, event, name):
                return "__ui__"

        try:
            self.top.handle_event(event, self.tooltip)
            selected = self.sidebar.handle_event(event, self.tooltip)
        except Exception as exc:
            self._report_ui_error("Навігація", exc)
            return "__ui__"
        if selected:
            if self.progression_panel:
                state, reason = self.progression_panel.progression.section_state(selected)
                if state == "LOCKED":
                    self.bottom.push(f"РОЗДІЛ ЗАБЛОКОВАНО: {selected}. Умова відкриття: {reason}")
                    self.sidebar.active = self.current_section
                    return "__ui__"
            self.current_section = selected
            self.right.set_section(selected)
            panel_routes = (
                (self.galaxy_panel, "Галактична карта"),
                (self.colony_panel, "Планети"),
                (self.automation_panel, "Автоматизація"),
                (self.trade_panel, "Торгівля"),
                (self.campaign_panel, "Кампанія"),
                (self.settings_panel, "Налаштування"),
            )
            for panel, section in panel_routes:
                if panel:
                    if selected == section:
                        panel.open()
                    else:
                        panel.close()
            if self.progression_panel:
                if selected == "Прогрес":
                    self.progression_panel.open()
                elif not self.progression_panel.visible:
                    self.progression_panel.close()
            if selected == "Будівництво":
                self.build_panel.open()
                self.mining_panel.close()
                if self.fleet_panel: self.fleet_panel.close()
                if self.research_panel: self.research_panel.close()
            elif selected == "Видобуток":
                self.mining_panel.open()
                self.build_panel.close()
                if self.fleet_panel: self.fleet_panel.close()
                if self.research_panel: self.research_panel.close()
            elif selected == "Флот":
                self.build_panel.close()
                self.mining_panel.close()
                if self.fleet_panel: self.fleet_panel.open()
                if self.research_panel: self.research_panel.close()
            elif selected == "Дослідження":
                self.build_panel.close()
                self.mining_panel.close()
                if self.fleet_panel: self.fleet_panel.close()
                if self.research_panel: self.research_panel.open()
            else:
                self.build_panel.close()
                self.mining_panel.close()
                if self.fleet_panel: self.fleet_panel.close()
                if self.research_panel: self.research_panel.close()
            self.bottom.push(f"Відкрито розділ: {selected}")
            return selected
        if event.type == pygame.MOUSEMOTION and self.sidebar.hovered is None:
            if not any(r.collidepoint(event.pos) for r in self.top.resource_rects.values()):
                self.tooltip.text = None
        return None

    def update(self, dt):
        self.right.update(dt)
        self.sidebar.update(dt)

    def draw(self, surface, station_selected):
        for component, callback in (
            ("Верхня панель", lambda: self.top.draw(surface)),
            ("Бічне меню", lambda: self.sidebar.draw(surface)),
            ("Права панель", lambda: self.right.draw(surface, station_selected)),
            ("Журнал подій", lambda: self.bottom.draw(surface)),
        ):
            try:
                callback()
            except Exception as exc:
                self._report_ui_error(component, exc)
        self._safe_panel_draw(self.build_panel, surface, "Будівництво")
        self._safe_panel_draw(self.mining_panel, surface, "Видобуток")
        self._safe_panel_draw(self.fleet_panel, surface, "Флот")
        self._safe_panel_draw(self.research_panel, surface, "Дослідження")
        try:
            self.tooltip.draw(surface)
        except Exception as exc:
            self._report_ui_error("Підказки", exc)
        self._safe_panel_draw(self.galaxy_panel, surface, "Галактична карта")
        self._safe_panel_draw(self.colony_panel, surface, "Планети")
        self._safe_panel_draw(self.automation_panel, surface, "Автоматизація")
        self._safe_panel_draw(self.trade_panel, surface, "Торгівля")
        self._safe_panel_draw(self.campaign_panel, surface, "Кампанія")
        self._safe_panel_draw(self.settings_panel, surface, "Налаштування")
        self._safe_panel_draw(self.offline_report, surface, "Офлайн-звіт")
        self._safe_panel_draw(self.progression_panel, surface, "Прогрес")

```

### `ui/panel_guard.py`
```python
"""Fault isolation for HUD panels without silently closing the panel.

A transient rendering/input exception must not mutate navigation state. The
panel remains visible and the caller can display a diagnostic overlay.
"""
from __future__ import annotations


class PanelGuard:
    def __init__(self, on_error=None):
        self.on_error = on_error
        self.errors = {}

    def _failed(self, component, exc):
        message = f"{type(exc).__name__}: {exc}"
        previous = self.errors.get(component)
        self.errors[component] = message
        if self.on_error and previous != message:
            self.on_error(component, exc)
        return message

    def handle_event(self, panel, event, component):
        if panel is None or not getattr(panel, "visible", False):
            return False
        try:
            handled = bool(panel.handle_event(event))
            self.errors.pop(component, None)
            return handled
        except Exception as exc:
            self._failed(component, exc)
            # Consume the failing event, but preserve panel visibility and state.
            return True

    def draw(self, panel, surface, component):
        if panel is None or not getattr(panel, "visible", False):
            return False
        try:
            panel.draw(surface)
            self.errors.pop(component, None)
            return True
        except Exception as exc:
            self._failed(component, exc)
            # Crucially, do not set panel.visible=False here.
            return False

```

### `tests/test_panel_guard.py`
```python
import unittest
from types import SimpleNamespace

from ui.panel_guard import PanelGuard


class PanelGuardTests(unittest.TestCase):
    def test_draw_exception_never_closes_panel_during_30_second_session(self):
        calls = []
        guard = PanelGuard(lambda component, exc: calls.append((component, str(exc))))
        panel = SimpleNamespace(visible=True)
        panel.draw = lambda surface: (_ for _ in ()).throw(RuntimeError("simulated draw failure"))
        for _ in range(30 * 60):
            guard.draw(panel, object(), "Будівництво")
            self.assertTrue(panel.visible)
        self.assertEqual(len(calls), 1)
        self.assertIn("simulated draw failure", guard.errors["Будівництво"])

    def test_event_exception_is_consumed_without_closing_or_resetting_panel(self):
        guard = PanelGuard()
        panel = SimpleNamespace(visible=True, selected_id="solar_array")
        panel.handle_event = lambda event: (_ for _ in ()).throw(ValueError("bad event"))
        self.assertTrue(guard.handle_event(panel, object(), "Будівництво"))
        self.assertTrue(panel.visible)
        self.assertEqual(panel.selected_id, "solar_array")

    def test_successful_draw_clears_previous_error(self):
        guard = PanelGuard()
        panel = SimpleNamespace(visible=True, draw=lambda surface: None)
        guard.errors["Будівництво"] = "old failure"
        self.assertTrue(guard.draw(panel, object(), "Будівництво"))
        self.assertNotIn("Будівництво", guard.errors)


if __name__ == "__main__":
    unittest.main()

```

### `tests/test_release_package.py`
```python
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

if __name__=="__main__": unittest.main()

```
