"""Contextual information panel for the selected station or HUD section."""
import pygame
from ui import theme

class RightPanel:
    WIDTH = 260

    @staticmethod
    def width_for(screen_width):
        return max(150, min(RightPanel.WIDTH, int(screen_width * 0.24)))

    def __init__(self):
        self.slide = 0.0
        self.target = 1.0
        self.section = "Огляд"

    def set_section(self, section):
        self.section = section
        self.target = 1.0

    def update(self, dt):
        self.slide += (self.target - self.slide) * min(1.0, dt * 8.0)

    def draw(self, surface, station_selected):
        w, h = surface.get_size()
        width = self.width_for(w)
        x = w - width - 12
        y = 86
        panel_h = max(360, h - 190)
        # Slight slide from the right edge.
        x += int((1.0 - self.slide) * (width + 20))
        r = pygame.Rect(x, y, width, panel_h).clip(surface.get_rect())
        theme.panel(surface, r, fill=(7, 17, 32), border=theme.BORDER_BRIGHT)
        theme.label(surface, "TACTICAL DATA", (x + 16, y + 15), 10, theme.MUTED, True)
        pygame.draw.line(surface, theme.BORDER, (x + 14, y + 40), (x + width - 14, y + 40))
        title = "ОРБІТАЛЬНА СТАНЦІЯ" if self.section == "Огляд" else self.section.upper()
        theme.label(surface, title, (x + 16, y + 55), 14, theme.CYAN, True)
        if self.section == "Огляд":
            theme.label(surface, "STATION • ATLAS-01", (x + 16, y + 83), 11, theme.TEXT, True)
            theme.label(surface, "Статус", (x + 16, y + 116), 11, theme.MUTED)
            pygame.draw.circle(surface, theme.GREEN, (x + 132, y + 121), 4)
            theme.label(surface, "ONLINE", (x + 143, y + 114), 10, theme.GREEN, True)
            stats = [("◈  Корпус", "94%", .94, theme.GREEN),
                     ("ϟ  Енергосистема", "87%", .87, theme.CYAN),
                     ("♙  Екіпаж", "128 / 150", 128/150, theme.PURPLE),
                     ("▦  Модулі", "10", .66, theme.GOLD)]
            sy = y + 148
            for name, value, ratio, tint in stats:
                theme.label(surface, name, (x + 16, sy), 11, theme.MUTED)
                theme.label(surface, value, (x + 151, sy), 11, theme.TEXT, True)
                track = pygame.Rect(x + 16, sy + 19, width - 32, 5)
                pygame.draw.rect(surface, (22, 39, 57), track, border_radius=3)
                pygame.draw.rect(surface, tint,
                                 (track.x, track.y, max(2, int(track.width * ratio)), track.height),
                                 border_radius=3)
                sy += 48
            pygame.draw.line(surface, theme.BORDER, (x + 15, sy), (x + width - 15, sy))
            theme.label(surface, "ENERGY OUTPUT", (x + 16, sy + 18), 10, theme.MUTED, True)
            pygame.draw.rect(surface, (24, 43, 60), (x + 16, sy + 39, self.WIDTH - 32, 8), border_radius=4)
            pygame.draw.rect(surface, theme.CYAN, (x + 16, sy + 39, int((self.WIDTH - 32) * .78), 8), border_radius=4)
            theme.label(surface, "78%", (x + width - 48, sy + 55), 11, theme.CYAN, True)
        else:
            theme.label(surface, "РОЗДІЛ У РОЗРОБЦІ", (x + 16, y + 91), 12, theme.GOLD, True)
            lines = ["Інтерфейс розділу активний.",
                     "Ігрові механіки будуть",
                     "підключені на наступних",
                     "етапах розробки."]
            for i, line in enumerate(lines):
                theme.label(surface, line, (x + 16, y + 125 + i * 23), 12, theme.MUTED)
            theme.panel(surface, pygame.Rect(x + 16, y + 245, self.WIDTH - 32, 62),
                        fill=(10, 27, 44), border=theme.BORDER, radius=5)
            pygame.draw.circle(surface, theme.GOLD, (x + 29, y + 274), 4)
            theme.label(surface, "MODULE STATUS", (x + 42, y + 254), 8, theme.MUTED, True)
            theme.label(surface, "IN DEVELOPMENT", (x + 42, y + 271), 10, theme.GOLD, True)
