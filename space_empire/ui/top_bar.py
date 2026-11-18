"""Live resource strip with detailed per-resource hover information."""
import pygame
from ui import theme


class TopBar:
    HEIGHT = 66
    RESOURCE_ORDER = ("metal", "energy", "crystals", "fuel", "credits", "science")

    def __init__(self, resource_manager, progression=None):
        self.resource_manager = resource_manager
        self.progression = progression
        self.resource_rects = {}

    @staticmethod
    def _format_amount(value):
        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if value >= 10_000:
            return f"{value / 1_000:.1f}K"
        if value >= 1_000:
            return f"{value / 1_000:.2f}K"
        return f"{value:.1f}".rstrip("0").rstrip(".")

    @staticmethod
    def _rate(value):
        return f"{value:+.2f}/с"

    def tooltip_text(self, key):
        r = self.resource_manager.get(key)
        return (
            f"{r.name} | Запас: {r.amount:,.1f} / {r.capacity:,.1f} | "
            f"Виробництво: +{r.production:.2f}/с | "
            f"Споживання: -{r.consumption:.2f}/с | Баланс: {self._rate(r.balance)}"
        )

    def handle_event(self, event, tooltip):
        if event.type == pygame.MOUSEMOTION:
            for key, rect in self.resource_rects.items():
                if rect.collidepoint(event.pos):
                    tooltip.set(self.tooltip_text(key), event.pos)
                    return
            # Do not clear a tooltip owned by another HUD element.
            if tooltip.text and tooltip.text.split(" | ", 1)[0] in (
                self.resource_manager.get(k).name for k in self.RESOURCE_ORDER
            ):
                tooltip.text = None

    def draw(self, surface):
        w = surface.get_width()
        rect = pygame.Rect(12, 10, w - 24, self.HEIGHT)
        theme.panel(surface, rect, fill=(7, 17, 33), border=theme.BORDER_BRIGHT)
        theme.label(surface, "SPACE EMPIRE", (28, 17), 20, theme.CYAN, True)
        theme.label(surface, "COMMAND NETWORK  •  SECTOR 07", (29, 43), 9, theme.MUTED)
        pygame.draw.line(surface, (26, 64, 91), (28, 60), (190, 60), 1)

        start_x = min(320, max(235, int(w * 0.205)))
        right_x = w - 166
        available = max(480, right_x - start_x - 10)
        cell_w = available / len(self.RESOURCE_ORDER)
        self.resource_rects.clear()
        for i, key in enumerate(self.RESOURCE_ORDER):
            resource = self.resource_manager.get(key)
            x = int(start_x + i * cell_w)
            cell = pygame.Rect(x - 7, 14, max(50, int(cell_w - 3)), 56)
            self.resource_rects[key] = cell
            if i:
                pygame.draw.line(surface, (31, 75, 103), (x - 12, 20), (x - 12, 61), 1)

            theme.resource_glyph(surface, (x + 9, 38), resource.color, key, 10)
            theme.label(surface, resource.name.upper(), (x + 26, 16), 8, theme.MUTED, True)
            theme.label(surface, self._format_amount(resource.amount), (x + 26, 28),
                        17, theme.TEXT, True)

            balance_color = theme.GREEN if resource.balance > 0.001 else (
                theme.RED if resource.balance < -0.001 else theme.MUTED)
            theme.label(surface, self._rate(resource.balance), (x + 26, 49),
                        9, balance_color, True)
            # Tiny production/consumption split is available at a glance.
            if cell_w >= 150 and (resource.production > 0 or resource.consumption > 0):
                split = f"ВИР +{resource.production:.1f}  СПОЖ -{resource.consumption:.1f}"
                theme.label(surface, split, (x + 87, 51), 7, theme.MUTED)

        commander_x = w - 151
        pygame.draw.line(surface, theme.BORDER, (commander_x - 13, 20),
                         (commander_x - 13, 61), 1)
        theme.label(surface, "COMMANDER", (commander_x, 14), 8, theme.MUTED, True)
        level = int(getattr(self.progression, "commander_level", 1))
        xp = int(getattr(self.progression, "commander_xp", 0))
        theme.label(surface, f"LEVEL {level:02d}", (commander_x, 28), 13, theme.GREEN, True)
        theme.label(surface, f"XP {xp}", (commander_x, 46), 8, theme.MUTED)
