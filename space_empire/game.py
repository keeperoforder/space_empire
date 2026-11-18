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
    def __init__(self, load_saved: bool = True, developer_mode: bool = False) -> None:
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)

        self.is_fullscreen = config.START_FULLSCREEN
        self.screen = self._create_display()
        self.clock = pygame.time.Clock()
        self.running = True
        self.delta_time = 0.0
        self.fps = 0.0
        self._fps_font = pygame.font.SysFont('consolas', 12)

        self.developer_mode_enabled = bool(developer_mode)
        self.dev_save_dir = Path(__file__).resolve().parent / "saves" / "developer"
        save_path = self.dev_save_dir / "developer_save.json" if developer_mode else "saves/space_empire_save.json"
        self.save_manager = SaveManager(path=save_path)
        if not load_saved and not developer_mode:
            # Normal new-game archival is unchanged; Developer Mode has its own slot.
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
            technology_save_path = (self.dev_save_dir / "technology_progress.json"
                                     if developer_mode else
                                     Path(__file__).resolve().parent / "technology" / "progress.json")
        if not load_saved and not developer_mode and technology_save_path.exists():
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
            enabled=(load_saved or developer_mode)
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
        self.dev_tools = None
        if developer_mode:
            from developer.dev_mode import DeveloperMode
            self.dev_tools = DeveloperMode(self)
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
            if self.dev_tools and self.dev_tools.handle_event(event):
                continue
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
        if self.dev_tools:
            if self.dev_tools.paused:
                dt = 0.0
            else:
                dt *= self.dev_tools.speed
        if self.progression.is_unlocked("campaign") or (self.dev_tools and self.campaign_manager.enabled):
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
        self._sync_completed_buildings()
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

    def _sync_completed_buildings(self):
        for completed in self.buildings.take_completed_buildings():
            definition = self.buildings.definition(completed["building_id"])
            if completed.get("upgrade"):
                self.station.upgrade_constructed_building(completed["building_id"])
            else:
                self.station.add_constructed_building(
                    completed["building_id"], definition["name"], definition["sprite"]
                )

    def draw(self) -> None:
        self.space_background.draw(self.screen, self.camera)
        galaxy_open = bool(self.hud.galaxy_panel and self.hud.galaxy_panel.visible)
        if not galaxy_open:
            self.station.draw(self.screen, self.camera)
            self.mining_visuals.draw(self.screen, self.camera)
            self.fleet_visuals.draw(self.screen, self.camera)
        self.hud.draw(self.screen, self.station.selected)
        if self.dev_tools:
            self.dev_tools.draw(self.screen)
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
