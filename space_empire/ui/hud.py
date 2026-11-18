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
from ui.panel_guard import PanelGuard


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
