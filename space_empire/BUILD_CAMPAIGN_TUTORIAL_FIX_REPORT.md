# Space Empire — виправлення будівництва, кампанії та навчання

## Діагностика

- Кампанія відображала дані окремого `CampaignManager`, який для нової гри навмисно створювався з `enabled=False`. Панель не використовувала активний `GameProgression`, тому початкове сюжетне завдання навчання не було джерелом даних кампанії.

- Будівництво сонячної панелі було закрите до переходу з етапу `awakening` на `power`. Раніше перехід залежав від ручного натискання аварійного збору у навчальному вікні; доки цей пролог не завершено, у конструкторі не було доступної сонячної панелі.

- Навчальне вікно не давало чіткої інструкції для етапу відновлення живлення.

## Виправлення

- На старті нової гри одноразовий аварійний вантаж автоматично зараховується як пролог. Це не створює нескінченного джерела ресурсів: `perform_salvage()` залишається одноразовим, його прапорець і нагорода зберігаються у прогресії. Після прологу активне завдання — відновити енергосистему.

- Кампанія тепер показує поточне завдання `GameProgression`, включно з текстом «Відновити енергосистему станції», підказкою та прогресом.

- Кнопка «Перейти до будівництва» перемикає активний розділ і відкриває реальний `BuildPanel`.

- Конструктор використовує наявний каталог: ціна сонячної панелі 90 металу, 20 енергії, 8 кристалів, 5 палива та 35 кредитів; час 12 секунд; виробництво +8 енергії/с після завершення.

- `BuildingManager` як і раніше списує ресурси при старті, додає будівлю після завершення таймера, перераховує економічні ефекти; `Game.update()` додає її процедурний спрайт до станції та просуває навчальне завдання.

## Перевірки

- 125/125 unittest PASS.
- compileall PASS.
- Pygame не встановлений у середовищі, тому реальний графічний запуск/клік-тест не виконаний. Логічний інтеграційний сценарій аварійного вантажу → сонячна панель → завершення будівництва → +8 енергії/с перевіряється тестами менеджерів.

## Повний код змінених файлів

### `game.py`
```python
"""Main game class and runtime loop."""
import pygame
from pathlib import Path
import os
import sys

import config
from graphics.camera import Camera
from graphics.background import SpaceBackground
from graphics.station import SpaceStation
from ui.hud import HUD
from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from graphics.mining_visuals import MiningVisuals
from fleet import FleetManager
from graphics.fleet_visuals import FleetVisuals
from technology import TechnologyManager
from save_system import SaveManager
from save_system.save_manager import archive_existing_files
from ui.offline_report import OfflineReport
from galaxy import GalaxyManager
from colonies import ColonyManager
from automation import AutomationManager, TradeManager
from campaign import CampaignManager
from progression import GameProgression


class Game:
    def __init__(self, load_saved: bool = True) -> None:
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)

        self.is_fullscreen = config.START_FULLSCREEN
        self.screen = self._create_display()
        self.clock = pygame.time.Clock()
        self.running = True
        self.delta_time = 0.0
        self.fps = 0.0
        self._fps_font = pygame.font.SysFont('consolas', 12)

        self.save_manager = SaveManager()
        if not load_saved:
            # Preserve the previous campaign before starting a fresh slot.
            # This is intentionally non-destructive: New Game never silently deletes saves.
            archive_existing_files(
                (self.save_manager.path, self.save_manager.backup_path),
                self.save_manager.path.parent / "archive"
            )

        self.camera = Camera()
        self.space_background = SpaceBackground(
            config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        )
        self.station = SpaceStation(position=(0, 0))
        self.economy = ResourceManager(new_game=not load_saved)
        self.resource_manager = self.economy  # Public API alias for gameplay systems.
        self.buildings = BuildingManager(self.economy)
        self.building_manager = self.buildings
        self.mining = MiningManager(self.economy, initial_ship_count=0)
        self.mining_manager = self.mining
        self.mining_visuals = MiningVisuals(self.mining)
        self.fleet = FleetManager(self.economy, self.buildings, self.mining)
        self.fleet_manager = self.fleet
        self.fleet_visuals = FleetVisuals(self.fleet)
        if getattr(sys, "frozen", False):
            data_root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "SpaceEmpire"
            data_root.mkdir(parents=True, exist_ok=True)
            technology_save_path = data_root / "technology_progress.json"
        else:
            technology_save_path = Path(__file__).resolve().parent / "technology" / "progress.json"
        if not load_saved and technology_save_path.exists():
            archive_existing_files(
                (technology_save_path,), technology_save_path.parent / "archive"
            )
        self.technology = TechnologyManager(self.economy, save_path=technology_save_path)
        self.technology_manager = self.technology
        self._applied_technology_bonuses = None
        self._apply_technology_bonuses()
        self.station_level = 1
        self.opened_planets = []
        self.colonies = []
        self.galaxy = GalaxyManager(self.economy)
        self.galaxy_manager = self.galaxy
        if not load_saved:
            for system in self.galaxy.systems.values():
                if system["id"] == "sol":
                    system["discovered"] = True
                    for obj in system.get("objects", []):
                        obj["revealed"] = False
                else:
                    system["discovered"] = False
                    for obj in system.get("objects", []):
                        obj["revealed"] = False
            self.galaxy._refresh_accessibility()
        self.colony_manager = ColonyManager(self.galaxy, self.fleet, self.economy)
        self.colonies_manager = self.colony_manager
        self.trade_manager = TradeManager(self.economy, self.fleet, self.colony_manager)
        self.automation_manager = AutomationManager(
            self.economy, self.buildings, self.mining, self.fleet,
            self.colony_manager, self.trade_manager
        )
        self.campaign_manager = CampaignManager(
            self.economy, self.buildings, self.mining, self.fleet,
            self.technology, self.galaxy, self.colony_manager,
            enabled=load_saved
        )
        self.progression = GameProgression(self.economy, self.buildings, self.technology)
        self.game_progression = self.progression
        self.mining.auto_dispatch_enabled = False
        if not load_saved:
            for key, setting in self.automation_manager.settings.items():
                if isinstance(setting, dict) and "enabled" in setting:
                    setting["enabled"] = False
            self.automation_manager.mining.auto_dispatch_enabled = False
            self.trade_manager.active = False
        self._save_timer = 0.0
        self._save_id = None
        self.hud = HUD(self.economy, self.buildings, self.station, self.mining,
                       self.fleet, self.technology, galaxy_manager=self.galaxy, colony_manager=self.colony_manager, automation_manager=self.automation_manager, trade_manager=self.trade_manager, campaign_manager=self.campaign_manager, game=self, progression=self.progression)
        saved = self.save_manager.load() if load_saved else None
        if saved is not None:
            report = self.save_manager.restore(self, saved, apply_offline=True)
            self.hud.offline_report = OfflineReport(report)
            for warning in self.save_manager.warnings:
                self.hud.bottom.push(warning)
            self.progression.refresh_section_access(self)
            self.hud.bottom.push("Попередню гру завантажено.")
        elif not load_saved:
            # The one-time wreckage manifest is the prologue reward. Apply it once
            # so the first actionable tutorial objective is restoring station power.
            ok, message = self.progression.perform_salvage()
            if ok:
                self.hud.bottom.push("ПРОЛОГ: аварійний вантаж автоматично доставлено на склад.")
                self.hud.bottom.push(message)
                for event_message in self.progression.take_events():
                    self.hud.bottom.push(event_message)
            else:
                self.hud.bottom.push(f"Не вдалося завершити аварійний пролог: {message}")
            self.progression.update(self)
            for event_message in self.progression.take_events():
                self.hud.bottom.push(event_message)
            # Save the post-prologue state before the first autosave interval.
            self.safe_save()

    def _create_display(self) -> pygame.Surface:
        if self.is_fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.RESIZABLE)
        return pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.RESIZABLE
        )

    def toggle_fullscreen(self) -> None:
        self.is_fullscreen = not self.is_fullscreen
        self.screen = self._create_display()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE and not self.is_fullscreen:
                self.screen = pygame.display.set_mode((max(960, event.w), max(600, event.h)), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.hud.bottom.push('Для виходу скористайтеся кнопкою закриття вікна.')
                elif event.key == pygame.K_q and event.mod & pygame.KMOD_CTRL:
                    self.running = False
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT:
                    self.toggle_fullscreen()
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    if not self._is_modal_open():
                        self.camera.add_zoom(config.CAMERA_ZOOM_SPEED)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    if not self._is_modal_open():
                        self.camera.add_zoom(-config.CAMERA_ZOOM_SPEED)
            elif event.type == pygame.MOUSEWHEEL:
                if not self._is_modal_open():
                    self.camera.add_zoom(event.y * config.CAMERA_ZOOM_SPEED)

            # UI gets pointer input first; station selection only if click is
            # inside the unobstructed central viewport.
            section = self.hud.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and getattr(self, 'audio_manager', None):
                self.audio_manager.play_click()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not section:
                if self._is_in_hud(event.pos):
                    continue
                self.station.selected = self.station.contains_screen_point(
                    event.pos, self.camera, self.screen
                )

    def _is_modal_open(self):
        names = ("research_panel", "galaxy_panel", "colony_panel",
                 "automation_panel", "trade_panel", "campaign_panel",
                 "settings_panel", "offline_report")
        return any(getattr(getattr(self, "hud", None), name, None) is not None
                   and getattr(getattr(self.hud, name), "visible", False)
                   for name in names)

    def _is_in_hud(self, pos):
        x, y = pos
        w, h = self.screen.get_size()
        return (
            y <= 78 or
            (x <= 214 and 78 <= y <= h - 88) or
            (x >= w - 284 and 78 <= y <= h - 88) or
            y >= h - 98
        )

    def _apply_technology_bonuses(self):
        bonuses = dict(self.technology.bonuses)
        if bonuses == self._applied_technology_bonuses:
            return
        self.buildings.set_technology_bonuses(bonuses)
        self.mining.set_technology_bonuses(bonuses)
        self.fleet.set_technology_bonuses(bonuses)
        self._applied_technology_bonuses = bonuses

    def update(self, dt: float) -> None:
        if self.progression.is_unlocked("campaign"):
            self.campaign_manager.update(dt)
            for message in self.campaign_manager.take_events(): self.hud.bottom.push(message)
        self.technology.update(dt)
        self._apply_technology_bonuses()
        for message in self.technology.take_events():
            self.hud.bottom.push(message)
        self.camera.update(dt, pygame.key.get_pressed())
        self.space_background.update(dt)
        self.station.update(dt)
        self.buildings.update(dt)
        for completed in self.buildings.take_completed_buildings():
            definition = self.buildings.definition(completed["building_id"])
            if completed.get("upgrade"):
                self.station.upgrade_constructed_building(completed["building_id"])
            else:
                self.station.add_constructed_building(
                    completed["building_id"], definition["name"], definition["sprite"]
                )
        for message in self.buildings.take_completed_events():
            self.hud.bottom.push(message)
        self.progression.update(self)
        for message in self.progression.take_events():
            self.hud.bottom.push(message)
        self.mining.update(dt)
        for message in self.mining.take_events():
            self.hud.bottom.push(message)
        self.mining_visuals.update(dt)
        self.fleet.update(dt)
        self.galaxy.update(self.fleet)
        self.colony_manager.update(dt)
        self.automation_manager.update(dt)
        self.trade_manager.update(dt)
        for message in self.automation_manager.take_events():
            self.hud.bottom.push(message)
        for message in self.trade_manager.take_events():
            self.hud.bottom.push(message)
        for message in self.galaxy.take_events():
            self.hud.bottom.push(message)
        for message in self.colony_manager.take_events():
            self.hud.bottom.push(message)
        for message in self.fleet.take_events():
            self.hud.bottom.push(message)
        self.fleet_visuals.update(dt)
        self.economy.update(dt)
        self.hud.update(dt)
        self._save_timer += dt
        if self._save_timer >= 30.0:
            self.safe_save()
            self._save_timer %= 30.0

    def draw(self) -> None:
        self.space_background.draw(self.screen, self.camera)
        galaxy_open = bool(self.hud.galaxy_panel and self.hud.galaxy_panel.visible)
        if not galaxy_open:
            self.station.draw(self.screen, self.camera)
            self.mining_visuals.draw(self.screen, self.camera)
            self.fleet_visuals.draw(self.screen, self.camera)
        self.hud.draw(self.screen, self.station.selected)
        if config.SHOW_FPS:
            fps_surface = self._fps_font.render(f"FPS {self.fps:5.1f}", True, (105, 190, 220))
            self.screen.blit(fps_surface, (self.screen.get_width() - 78, self.screen.get_height() - 22))
        pygame.display.flip()

    def safe_save(self) -> bool:
        try:
            self.save_manager.save(self)
            return True
        except (OSError, ValueError, TypeError) as exc:
            if hasattr(self, "hud"):
                self.hud.bottom.push(f"Помилка збереження: {exc}")
            print(f"Space Empire save failed: {exc}", file=sys.stderr)
            return False

    def run(self) -> None:
        try:
            while self.running:
                self.delta_time = min(0.1, self.clock.tick(config.TARGET_FPS) / 1000.0)
                self.fps = self.clock.get_fps()
                self.handle_events()
                if not self.running:
                    break
                self.update(self.delta_time)
                self.draw()
        finally:
            try:
                self.safe_save()
            finally:
                pygame.quit()


if __name__ == "__main__":
    Game().run()

```

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
        if panel is None or not getattr(panel, "visible", False):
            return False
        try:
            return bool(panel.handle_event(event))
        except Exception as exc:
            panel.visible = False
            self._report_ui_error(component, exc)
            return True

    def _safe_panel_draw(self, panel, surface, component):
        if panel is None:
            return
        try:
            panel.draw(surface)
        except Exception as exc:
            panel.visible = False
            self._report_ui_error(component, exc)

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

### `ui/campaign_panel.py`
```python
"""Campaign journal with the active tutorial objective and quick navigation."""
import pygame
from ui import theme


class CampaignPanel:
    def __init__(self, manager, bottom, progression=None, on_build=None):
        self.manager, self.bottom = manager, bottom
        self.progression = progression
        self.on_build = on_build
        self.visible = False
        self.scroll = 0
        self.choice_rects = []
        self.close_rect = pygame.Rect(0, 0, 1, 1)
        self.build_rect = pygame.Rect(0, 0, 1, 1)

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False

    def handle_event(self, event):
        if not self.visible:
            return False
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * 32)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.build_rect.collidepoint(event.pos):
                if self.on_build:
                    self.on_build()
                self.close()
                self.bottom.push("Відкрито конструктор станції.")
                return True
            if self.manager.active_event:
                for rect, cid in self.choice_rects:
                    if rect.collidepoint(event.pos):
                        ok, msg = self.manager.choose_event(cid)
                        self.bottom.push(msg)
                        return True
            if self.close_rect.collidepoint(event.pos):
                self.close()
            return True
        return False

    def _wrap(self, surface, text, rect, color, size=14, limit=4):
        font = pygame.font.SysFont("segoeui", size)
        words, lines, line = str(text).split(), [], ""
        for word in words:
            candidate = (line + " " + word).strip()
            if font.size(candidate)[0] > rect.width and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        for i, value in enumerate(lines[:limit]):
            surface.blit(font.render(value, True, color), (rect.x, rect.y + i * (size + 4)))

    def draw(self, surface):
        if not self.visible:
            return
        w, h = surface.get_size()
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((1, 5, 15, 215))
        surface.blit(shade, (0, 0))
        panel = pygame.Rect(220, 86, w - 500, h - 176)
        theme.panel(surface, panel, fill=(7, 17, 32))
        pygame.draw.rect(surface, theme.BORDER_BRIGHT, panel, 1, border_radius=9)
        title = "КОСМІЧНА ПОДІЯ" if self.manager.active_event else "СЮЖЕТНА КАМПАНІЯ"
        theme.label(surface, title, (panel.x + 24, panel.y + 17), 19, theme.CYAN, True)
        self.close_rect = pygame.Rect(panel.right - 42, panel.y + 12, 30, 30)
        theme.label(surface, "×", (self.close_rect.x + 8, self.close_rect.y), 24, theme.TEXT, True)

        # The tutorial progression is the source of truth for the opening campaign.
        if self.progression is not None and not self.manager.active_event:
            stage = self.progression.current_task()
            if stage is None:
                theme.label(surface, "Початкову кампанію завершено.",
                            (panel.x + 24, panel.y + 80), 22, theme.GREEN, True)
                theme.label(surface, "Усі базові механіки імперії відкриті.",
                            (panel.x + 24, panel.y + 120), 14, theme.MUTED)
                self.build_rect = pygame.Rect(0, 0, 1, 1)
                return
            task_title = ("Відновити енергосистему станції"
                          if stage.get("id") == "power" else stage.get("title", "Активне завдання"))
            theme.label(surface, f"АКТИВНЕ ЗАВДАННЯ • ЕТАП {self.progression.stage_index + 1:02d}/10",
                        (panel.x + 24, panel.y + 67), 11, theme.GREEN, True)
            theme.label(surface, task_title, (panel.x + 24, panel.y + 100),
                        24, theme.TEXT, True)
            self._wrap(surface, stage.get("description", ""),
                       pygame.Rect(panel.x + 24, panel.y + 145, panel.width - 48, 76),
                       theme.MUTED, 15, 4)
            objective = stage.get("objective", {})
            theme.label(surface, objective.get("label", task_title),
                        (panel.x + 24, panel.y + 240), 16, theme.CYAN, True)
            if stage.get("id") == "power":
                hint = "Підказка: натисніть «Будівництво», виберіть «Сонячна панель» і натисніть «Побудувати»."
            else:
                hint = "Підказка: виконайте ціль у відповідному розділі станції."
            self._wrap(surface, hint,
                       pygame.Rect(panel.x + 24, panel.y + 278, panel.width - 48, 54),
                       theme.GOLD, 13, 3)
            progress = self.progression._last_objective_progress
            target = objective.get("count", objective.get("target", 1))
            theme.label(surface, f"Прогрес: {progress} / {target}",
                        (panel.x + 24, panel.y + 340), 12, theme.GREEN)
            self.build_rect = pygame.Rect(panel.x + 24, panel.bottom - 66, 270, 40)
            pygame.draw.rect(surface, (12, 67, 91), self.build_rect, border_radius=5)
            pygame.draw.rect(surface, theme.CYAN, self.build_rect, 1, border_radius=5)
            theme.label(surface, "ПЕРЕЙТИ ДО БУДІВНИЦТВА",
                        (self.build_rect.x + 13, self.build_rect.y + 13), 10, theme.TEXT, True)
            return

        self.build_rect = pygame.Rect(0, 0, 1, 1)
        if self.manager.active_event:
            e = self.manager.active_event
            art = pygame.Rect(panel.x + 24, panel.y + 60, 245, 190)
            pygame.draw.rect(surface, (10, 35, 57), art, border_radius=8)
            pygame.draw.rect(surface, theme.CYAN, art, 1, border_radius=8)
            cx, cy = art.center
            for r in (34, 57, 80):
                pygame.draw.circle(surface, (31, 105, 140), (cx, cy), r, 1)
            if e["illustration"] in ("ship", "asteroid", "artifact"):
                pygame.draw.polygon(surface, (110, 137, 154),
                    [(cx-55,cy),(cx-18,cy-40),(cx+43,cy-25),(cx+55,cy+15),(cx,cy+43)])
                pygame.draw.circle(surface, theme.CYAN, (cx+12,cy-4), 7)
            else:
                for r in range(20, 75, 12):
                    pygame.draw.arc(surface, theme.CYAN, (cx-r,cy-r,2*r,2*r), .2, 2.8, 2)
            theme.label(surface, e["category"].upper(), (art.x+12,art.bottom-23), 10, theme.CYAN, True)
            theme.label(surface, e["title"], (art.right+22,art.y+5), 21, theme.TEXT, True)
            self._wrap(surface,e["description"],pygame.Rect(art.right+22,art.y+42,panel.right-art.right-55,110),theme.MUTED,15,5)
            self.choice_rects = []
            y = art.bottom + 22
            for choice in e["choices"]:
                rect = pygame.Rect(panel.x+24,y,panel.width-48,62)
                pygame.draw.rect(surface,(13,39,59),rect,border_radius=6)
                pygame.draw.rect(surface,theme.BORDER,rect,1,border_radius=6)
                theme.label(surface,choice["label"],(rect.x+13,rect.y+7),14,theme.CYAN,True)
                self._wrap(surface,choice["description"],pygame.Rect(rect.x+13,rect.y+30,rect.width-26,26),theme.MUTED,11,1)
                self.choice_rects.append((rect,choice["id"]))
                y += 71
            return

        ch = self.manager.current_chapter()
        if not ch:
            theme.label(surface, "Дані кампанії поки недоступні.",
                        (panel.x + 24, panel.y + 70), 14, theme.MUTED)
            return
        theme.label(surface,ch["title"],(panel.x+24,panel.y+56),22,theme.TEXT,True)
        self._wrap(surface,ch.get("story", ""),pygame.Rect(panel.x+24,panel.y+91,panel.width-48,60),theme.MUTED,14,4)
        area=pygame.Rect(panel.x+18,panel.y+160,panel.width-36,panel.height-176)
        clip=surface.get_clip()
        surface.set_clip(area)
        y=area.y-self.scroll
        for chapter in self.manager.chapters:
            complete=all(self.manager.missions[x]["status"]=="completed" for x in chapter["missions"])
            theme.label(surface,("✓ " if complete else "◇ ")+chapter["title"],(area.x+8,y),14,theme.GREEN if complete else theme.CYAN,True)
            y+=25
            for mid in chapter["missions"]:
                mission=self.manager.missions[mid]
                color=theme.GREEN if mission["status"]=="completed" else theme.TEXT if mission["status"]=="available" else theme.MUTED
                theme.label(surface,mission["title"],(area.x+25,y),12,color,mission["status"]=="available")
                target=max(1,mission["objective"].get("amount",1))
                progress=min(1,float(mission.get("progress",0))/target)
                bar=pygame.Rect(area.x+260,y+3,180,7)
                pygame.draw.rect(surface,(25,43,60),bar,border_radius=3)
                pygame.draw.rect(surface,theme.CYAN,(bar.x,bar.y,int(bar.width*progress),7),border_radius=3)
                status={"completed":"ВИКОНАНО","available":"АКТИВНА","locked":"ЗАБЛОКОВАНА"}[mission["status"]]
                theme.label(surface,status,(bar.right+12,y),10,color,True)
                y+=17
                objective=mission["objective"]
                condition=f"Умова: {objective.get('key',objective.get('type','ціль'))} — {objective.get('amount',1)}"
                self._wrap(surface,mission.get("description",condition),pygame.Rect(area.x+25,y,area.width-55,28),theme.MUTED,10,1)
                reward_text="Нагорода: "+", ".join(f"{k} +{v}" for k,v in mission.get("rewards",{}).items())
                theme.label(surface,reward_text,(area.x+25,y+13),9,theme.CYAN if mission["status"]!="locked" else theme.MUTED)
                y+=31
            y+=10
        surface.set_clip(clip)

```

### `ui/progression_panel.py`
```python
"""Reusable tutorial briefing and single-active-quest panel."""
import pygame
from ui import theme


class ProgressionPanel:
    def __init__(self, progression, bottom):
        self.progression, self.bottom = progression, bottom
        self.visible = True
        self.action_rect = pygame.Rect(0, 0, 1, 1)
        self.dismiss_rect = pygame.Rect(0, 0, 1, 1)
        self.replay_rect = pygame.Rect(0, 0, 1, 1)
        self._replay_text = None

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False
        self.progression.mark_intro_seen()

    def handle_event(self, event):
        if not self.visible or event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.action_rect.collidepoint(event.pos):
            ok, message = self.progression.perform_salvage()
            self.bottom.push(message, theme.GREEN if ok else theme.RED)
            for item in self.progression.take_events():
                self.bottom.push(item)
            return True
        if self.replay_rect.collidepoint(event.pos):
            self._replay_text = self.progression.replay_explanation()
            return True
        if self.dismiss_rect.collidepoint(event.pos):
            self.close()
            return True
        return True

    def draw(self, surface):
        if not self.visible:
            return
        w, h = surface.get_size()
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((1, 5, 15, 205))
        surface.blit(shade, (0, 0))
        panel = pygame.Rect(max(180, w // 2 - 350), max(80, h // 2 - 235), 700, 470)
        theme.panel(surface, panel, fill=(7, 17, 32))
        pygame.draw.rect(surface, theme.BORDER_BRIGHT, panel, 1, border_radius=9)
        stage = self.progression.current_task()
        theme.label(surface, "ЦЕНТР НАВЧАННЯ • ПРОТОКОЛ ВІДНОВЛЕННЯ",
                    (panel.x + 24, panel.y + 20), 13, theme.CYAN, True)
        if stage:
            number = self.progression.stage_index + 1
            theme.label(surface, f"ЕТАП {number:02d} / 10", (panel.x + 24, panel.y + 52),
                        10, theme.GREEN, True)
            theme.label(surface, stage["title"], (panel.x + 24, panel.y + 75),
                        26, theme.TEXT, True)
            self._wrapped(surface, stage["description"],
                          pygame.Rect(panel.x + 24, panel.y + 116, panel.width - 48, 76),
                          theme.MUTED, 14, 3)
            objective = stage["objective"]
            theme.label(surface, "ЄДИНЕ АКТИВНЕ ЗАВДАННЯ", (panel.x + 24, panel.y + 207),
                        10, theme.CYAN, True)
            theme.label(surface, objective.get("label", stage["title"]),
                        (panel.x + 24, panel.y + 230), 17, theme.TEXT, True)
            progress = self.progression._last_objective_progress
            target = objective.get("count", objective.get("target", 1))
            if objective["type"] == "buildings":
                progress_text = "Виконати обидві вимоги"
            else:
                progress_text = f"Поточний прогрес: {progress} / {target}"
            theme.label(surface, progress_text, (panel.x + 24, panel.y + 258),
                        11, theme.GREEN)
            mechanics = ", ".join(self.progression.MECHANIC_LABELS.get(x, x)
                                  for x in stage.get("mechanics", []))
            theme.label(surface, "ВІДКРИЄТЬСЯ: " + (mechanics or "—"),
                        (panel.x + 24, panel.y + 286), 10, theme.CYAN)
            reward = stage.get("reward", {})
            reward_text = f"Нагорода: +{reward.get('xp', 0)} XP"
            if reward.get("resources"):
                reward_text += " • ресурси та матеріали для наступного етапу"
            theme.label(surface, reward_text, (panel.x + 24, panel.y + 311),
                        10, theme.GOLD)
            self.replay_rect = pygame.Rect(panel.x + 24, panel.bottom - 66, 190, 38)
            pygame.draw.rect(surface, (13, 31, 48), self.replay_rect, border_radius=5)
            pygame.draw.rect(surface, theme.BORDER, self.replay_rect, 1, border_radius=5)
            theme.label(surface, "ПОВТОРИТИ ПОЯСНЕННЯ",
                        (self.replay_rect.x + 10, self.replay_rect.y + 12), 9, theme.TEXT, True)
            self.action_rect = pygame.Rect(0, 0, 1, 1)
            if stage["id"] == "awakening":
                self.action_rect = pygame.Rect(panel.x + 230, panel.bottom - 66, 270, 38)
                pygame.draw.rect(surface, (12, 67, 91), self.action_rect, border_radius=5)
                pygame.draw.rect(surface, theme.CYAN, self.action_rect, 1, border_radius=5)
                theme.label(surface, "ЗАПУСТИТИ АВАРІЙНИЙ ЗБІР",
                            (self.action_rect.x + 12, self.action_rect.y + 12), 10, theme.TEXT, True)
            elif stage["id"] == "power":
                theme.label(surface, "ПІДКАЗКА: відкрийте «Будівництво» → «Сонячна панель» → «Побудувати».",
                            (panel.x + 230, panel.bottom - 54), 10, theme.GREEN)
            else:
                theme.label(surface, "Виконайте дію у відповідному розділі гри.",
                            (panel.x + 230, panel.bottom - 54), 10, theme.GREEN)
        else:
            theme.label(surface, "Початкову кампанію завершено.",
                        (panel.x + 24, panel.y + 110), 20, theme.GREEN, True)
            theme.label(surface, "Усі базові механіки імперії відкриті.",
                        (panel.x + 24, panel.y + 150), 13, theme.MUTED)
            self.action_rect = self.replay_rect = pygame.Rect(0, 0, 1, 1)
        if self._replay_text:
            self._wrapped(surface, self._replay_text,
                          pygame.Rect(panel.x + 24, panel.y + 350, panel.width - 48, 44),
                          theme.GOLD, 11, 2)
        self.dismiss_rect = pygame.Rect(panel.right - 150, panel.bottom - 66, 126, 38)
        pygame.draw.rect(surface, (13, 31, 48), self.dismiss_rect, border_radius=5)
        pygame.draw.rect(surface, theme.BORDER, self.dismiss_rect, 1, border_radius=5)
        theme.label(surface, "ПРОДОВЖИТИ",
                    (self.dismiss_rect.x + 12, self.dismiss_rect.y + 12), 10, theme.TEXT, True)

    @staticmethod
    def _wrapped(surface, text, rect, color, size, max_lines=4):
        font = pygame.font.SysFont("segoeui", size)
        words, lines, line = str(text).split(), [], ""
        for word in words:
            candidate = (line + " " + word).strip()
            if line and font.size(candidate)[0] > rect.width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        for index, value in enumerate(lines[:max_lines]):
            surface.blit(font.render(value, True, color), (rect.x, rect.y + index * (size + 4)))

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

if __name__=="__main__": unittest.main()

```
